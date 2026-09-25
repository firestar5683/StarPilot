"""Typed, versioned cache bytes. Live messages and native Params remain unchanged."""
from dataclasses import dataclass
import hashlib
import json
import struct

import capnp

from opendbc.car import structs as car
from openpilot.cereal import log

MAGIC = b"SPCACHE\x01"
MAX_HEADER_BYTES = 4096
MAX_ENVELOPE_BYTES = 32 * 1024 * 1024
MAX_PAYLOAD_BYTES = MAX_ENVELOPE_BYTES - MAX_HEADER_BYTES - len(MAGIC) - 4
FINGERPRINT_FORMAT = "capnp-transitive-node-v1"
EVENT_FINGERPRINT_FORMAT = "capnp-event-service-v2"


@dataclass(frozen=True)
class CacheContract:
  root: object
  service: str | None
  producer: str


# Vehicle flag and safety namespaces can change without changing the Cap'n Proto
# layout. Re-identify the vehicle instead of reusing flags from the old contract.
CONTRACTS = {
  "CarParamsCache": CacheContract(car.CarParams, None, "identified-car-params-v2"),
  "CarParamsPersistent": CacheContract(car.CarParams, None, "identified-car-params-v2"),
  "CarParamsPrevRoute": CacheContract(car.CarParams, None, "identified-car-params-v2"),
  "CalibrationParams": CacheContract(log.Event, "extrinsicsCalibration", "calibration-state-v1"),
  "LiveParametersV2": CacheContract(log.Event, "vehicleParameters", "vehicle-learner-v1"),
  "LiveTorqueParameters": CacheContract(log.Event, "lateralTorqueParameters", "torque-learner-v1"),
  "LiveDelay": CacheContract(log.Event, "lateralDelay", "delay-learner-v1"),
}
CACHE_KEYS = frozenset(CONTRACTS)


@dataclass(frozen=True)
class CacheInspection:
  status: str
  reason: str = ""
  payload: bytes | None = None
  schema_sha256: str | None = None


def _type_children(schema, descriptor):
  kind = next(iter(descriptor))
  if kind == "list":
    element = descriptor["list"]["elementType"]
    if next(iter(element)) in ("struct", "enum", "list"):
      yield from _type_children(schema.elementType, element)
  elif kind in ("struct", "enum"):
    yield schema


def schema_fingerprint(root_schema):
  """Hash complete compiled nodes and every referenced struct/enum, including groups.

  Node serialization retains names, ordinals, layouts, defaults, union tags and
  annotations. Root IDs alone are insufficient. Display-name changes intentionally
  invalidate a cache as a conservative compatibility boundary.
  """
  nodes = {}
  references = set()

  def collect_references(value):
    if isinstance(value, dict):
      for key, item in value.items():
        if key == "typeId":
          references.add(item)
        else:
          collect_references(item)
    elif isinstance(value, list):
      for item in value:
        collect_references(item)

  pending = [root_schema]
  while pending:
    schema = pending.pop()
    node = schema.node
    if node.id in nodes:
      continue
    nodes[node.id] = node.as_builder().to_bytes()
    descriptor = node.to_dict()
    if "struct" not in descriptor:
      continue
    for field in descriptor["struct"].get("fields", []):
      if "group" in field:
        collect_references(field["group"])
        pending.append(schema.fields[field["name"]].schema)
      else:
        collect_references(field["slot"]["type"])
        if next(iter(field["slot"]["type"])) in ("struct", "enum", "list"):
          pending.extend(_type_children(schema.fields[field["name"]].schema, field["slot"]["type"]))
  if references - nodes.keys():
    raise ValueError("Compiled schema contains unresolved transitive type references")
  digest = hashlib.sha256(FINGERPRINT_FORMAT.encode())
  digest.update(struct.pack(">Q", root_schema.node.id))
  for node_id, encoded in sorted(nodes.items()):
    digest.update(struct.pack(">QI", node_id, len(encoded)))
    digest.update(encoded)
  return digest.hexdigest()


def event_service_fingerprint(root_schema, service):
  descriptor = root_schema.node.to_dict()
  selected = root_schema.fields[service].proto
  if selected.discriminantValue == 65535 or selected.which() != "slot" or selected.slot.type.which() != "struct":
    raise ValueError("Event caches require a struct union service")
  fields = descriptor["struct"].pop("fields")
  descriptor["struct"].pop("discriminantCount")
  descriptor.pop("nestedNodes")
  digest = hashlib.sha256(EVENT_FINGERPRINT_FORMAT.encode())
  digest.update(json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode())
  # Unselected union arms do not describe the persisted message. Keep the actual
  # wrapper layout and every field/type needed to decode this service.
  for field in fields:
    if field["discriminantValue"] != 65535 and field["name"] != service:
      continue
    compiled = root_schema.fields[field["name"]]
    field_node = compiled.proto.as_builder()
    field_node.codeOrder = 0  # Declaration order can move when another union arm is added.
    encoded = field_node.to_bytes()
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)
    if "group" in field:
      children = (compiled.schema,)
    elif next(iter(field["slot"]["type"])) in ("struct", "enum", "list"):
      children = _type_children(compiled.schema, field["slot"]["type"])
    else:
      children = ()
    for child in children:
      digest.update(bytes.fromhex(schema_fingerprint(child)))
  return digest.hexdigest()


# Only process-owned compiled schemas are cached. Untrusted schemas are never
# memoized by numeric ID: two parsers can use identical IDs for different types.
_FINGERPRINTS = {}


def _fingerprint(contract, legacy=False):
  root_name = "car_params" if contract.root is car.CarParams else "event"
  service = contract.service if not legacy else None
  key = (root_name, service)
  if key not in _FINGERPRINTS:
    _FINGERPRINTS[key] = (event_service_fingerprint(contract.root.schema, service) if service is not None
                          else schema_fingerprint(contract.root.schema))
  return _FINGERPRINTS[key]


def prewarm_cache_contracts(keys=CACHE_KEYS):
  """Compute fingerprints during each producer/consumer process's startup."""
  result = {}
  for key in keys:
    contract = _contract(key)
    _fingerprint(contract, legacy=True)
    result[key] = _fingerprint(contract)
  return result


def _contract(key):
  if key not in CONTRACTS:
    raise ValueError(f"No typed cache contract for {key}")
  return CONTRACTS[key]


def _check_message(contract, message):
  if not isinstance(message, (capnp._DynamicStructBuilder, capnp._DynamicStructReader)):
    raise TypeError("Cache producers must supply a typed message, not serialized bytes")
  # Native schema equality identifies the actual compiled schema, not its type ID.
  # A schema loaded independently must not acquire current-producer provenance.
  if message.schema != contract.root.schema:
    raise ValueError("Cache message is not from the current compiled producer schema")
  if contract.service is not None and message.which() != contract.service:
    raise ValueError(f"Cache requires the {contract.service} service")


def _header(contract, key, payload, version=None):
  if version is None:
    version = 2 if contract.service is not None else 1
  if version not in (1, 2) or (version == 2 and contract.service is None):
    raise ValueError("Unsupported cache contract version")
  return {
    "version": version, "key": key, "producer_contract": contract.producer,
    "fingerprint_format": EVENT_FINGERPRINT_FORMAT if version == 2 else FINGERPRINT_FORMAT,
    "schema_sha256": _fingerprint(contract, legacy=version == 1),
    "root_id": hex(contract.root.schema.node.id), "service": contract.service,
    "payload_bytes": len(payload), "payload_sha256": hashlib.sha256(payload).hexdigest(),
  }


def put_cache(params, key, message, block=False):
  """Queue one atomic envelope, preserving the caller's existing Params block mode.

  The producer must create current-schema messages from current observations or a
  verified cache. Reinterpreting historical raw bytes with the current schema first
  cannot establish their origin and is not an authorized producer conversion.
  """
  contract = _contract(key)
  _check_message(contract, message)
  reader = message.as_reader() if isinstance(message, capnp._DynamicStructBuilder) else message
  # Clone before serialization so callers can reuse a builder already serialized
  # for a live message, without changing its write flag or queued contents.
  payload = reader.as_builder().to_bytes()
  if len(payload) > MAX_PAYLOAD_BYTES:
    raise ValueError("Cache payload exceeds the size limit")
  header = json.dumps(_header(contract, key, payload), sort_keys=True, separators=(",", ":")).encode()
  envelope = MAGIC + struct.pack(">I", len(header)) + header + payload
  if len(header) > MAX_HEADER_BYTES or len(envelope) > MAX_ENVELOPE_BYTES:
    raise ValueError("Cache envelope exceeds the size limit")
  params.put(key, envelope, block=block)


def _unique_members(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("Duplicate cache metadata member")
    result[key] = value
  return result


def inspect_cache(key, raw):
  """Check schema/producer/content provenance; no bytes are upgraded or activated."""
  contract = _contract(key)
  if raw is None:
    return CacheInspection("missing", "no stored value")
  if not isinstance(raw, bytes) or len(raw) < len(MAGIC) + 4 or not raw.startswith(MAGIC):
    return CacheInspection("incompatible", "missing versioned cache envelope")
  if len(raw) > MAX_ENVELOPE_BYTES:
    return CacheInspection("incompatible", "cache envelope exceeds the size limit")
  size = struct.unpack_from(">I", raw, len(MAGIC))[0]
  start = len(MAGIC) + 4
  if size > MAX_HEADER_BYTES or size == 0 or len(raw) < start + size:
    return CacheInspection("incompatible", "invalid envelope header length")
  payload = raw[start + size:]
  if not payload or len(payload) > MAX_PAYLOAD_BYTES:
    return CacheInspection("incompatible", "invalid cache payload length")
  try:
    header = json.loads(raw[start:start + size], object_pairs_hook=_unique_members)
    if not isinstance(header, dict) or type(header.get("version")) is not int or type(header.get("payload_bytes")) is not int:
      return CacheInspection("incompatible", "invalid cache metadata types")
    expected = _header(contract, key, payload, version=header["version"])
    if header != expected:
      return CacheInspection("incompatible", "cache metadata, schema or payload digest mismatch")
    with contract.root.from_bytes(payload, traversal_limit_in_words=MAX_PAYLOAD_BYTES // 8) as message:
      if contract.service is not None and message.which() != contract.service:
        return CacheInspection("incompatible", "cache payload has the wrong service")
  except (ValueError, UnicodeDecodeError, RecursionError, capnp.KjException) as error:
    return CacheInspection("incompatible", f"invalid cache encoding: {type(error).__name__}")
  return CacheInspection("valid", payload=payload, schema_sha256=expected["schema_sha256"])


def get_cache(params, key):
  """Return verified bytes or a cache miss; incompatible raw values are preserved."""
  return inspect_cache(key, params.get(key)).payload
