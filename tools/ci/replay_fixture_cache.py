"""Explicit cache conversion for reviewed, immutable replay recordings.

Published reference Event and CarParams use their producing schemas; input decoding
only compares firmware/VIN identity and does not prove the original input schema.
Input, reference and schemas are pinned before a current typed cache is made.
Unknown recordings require their own reviewed conversion, never current decoding.
"""

import hashlib
import json
from pathlib import Path
import tempfile

import capnp

from opendbc.car.structs import car
from openpilot.starpilot.schema_cache import put_cache
from openpilot.tools.lib.logreader import decompress_stream
from openpilot.tools.lib.url_file import URLFile


OPENPILOT_COMMIT = 'ec95db3f1fa19f76940497fedfdb62e09ea19912'
ARTIFACT_COMMIT = '9ae451c262c7402c9623f3baa1580c6242d6777b'
OPENDBC_COMMIT = '35f7e0813462607ef1d703e52313e7571e31405d'
TARGET_CAR_SHA256 = '1511eaaa36581a2182694e3cdf5a9b3cf05276e90c36bb5d82ee095e84c23d69'
FIXTURES = json.loads(Path(__file__).with_name('replay-fixture-cache.json').read_text())
# The reviewed target differs from the source only by SafetyModel.teslaPreap @39.
# No source field is dropped, renamed, defaulted or reinterpreted by this adapter.
SOURCE_FILES = {
  'car.capnp': ('opendbc', OPENDBC_COMMIT, 'opendbc/car/car.capnp',
                '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788'),
  'include/c++.capnp': ('opendbc', OPENDBC_COMMIT, 'opendbc/car/include/c++.capnp',
                      'fb306076cd38c27af1aed20fac6395e9a46fbe5b5df6a248b5f1b6845a079c44'),
  'log.capnp': ('openpilot', OPENPILOT_COMMIT, 'openpilot/cereal/log.capnp',
                '3f8906bd908494e20eb77b7d27536be541d4cf9f8d5277ae8528b3ee59a55673'),
  'custom.capnp': ('openpilot', OPENPILOT_COMMIT, 'openpilot/cereal/custom.capnp',
                  '6b06a0d2d5ac6b902ca2f433c1663ed83ea4b41ba4c16cddfc7acd8a630be82d'),
  'deprecated.capnp': ('openpilot', OPENPILOT_COMMIT, 'openpilot/cereal/deprecated.capnp',
                      'b3aa5c13de40001ed7376cef858500fb003f7698f96131cd0db18d878fa1af0d'),
}


def _digest(raw):
  return hashlib.sha256(raw).hexdigest()


class _Sink:
  def put(self, key, value, *, block):
    self.raw = value


def verified_fixture_params(segment: str, raw: bytes) -> dict[str, bytes]:
  """Create a cache only after independent source decoding and lossless conversion."""
  expected = FIXTURES.get(segment)
  if expected is None or len(raw) != expected['input_bytes'] or _digest(raw) != expected['input_sha256']:
    raise ValueError(f'{segment}: no reviewed immutable recording cache conversion')
  target_path = Path(__file__).resolve().parents[2] / 'opendbc_repo/opendbc/car/car.capnp'
  if _digest(target_path.read_bytes()) != TARGET_CAR_SHA256:
    raise ValueError('Replay cache target schema changed; review the source conversion')
  with tempfile.TemporaryDirectory(prefix='replay-source-schema-') as directory:
    root = Path(directory)
    for local, (repo, commit, path, digest) in SOURCE_FILES.items():
      source = URLFile(f'https://raw.githubusercontent.com/commaai/{repo}/{commit}/{path}').read()
      if _digest(source) != digest:
        raise ValueError(f'{local}: replay producing schema digest mismatch')
      destination = root / local
      destination.parent.mkdir(parents=True, exist_ok=True)
      destination.write_bytes(source)
    parser = capnp.SchemaParser()
    source_log = parser.load(str(root / 'log.capnp'), imports=[str(root)])
    reference_name = f'{segment.replace("|", "_")}_card_{OPENPILOT_COMMIT}.zst'
    reference = URLFile(f'https://raw.githubusercontent.com/commaai/ci-artifacts/{ARTIFACT_COMMIT}/{reference_name}').read()
    if len(reference) != expected['reference_bytes'] or _digest(reference) != expected['reference_sha256']:
      raise ValueError('Published replay CarParams reference digest mismatch')
    source_cp = next((message.carParams.to_dict()
                      for message in source_log.Event.read_multiple_bytes(decompress_stream(reference))
                      if message.which() == 'carParams'), None)
    if source_cp is None:
      raise ValueError('Published card reference is missing CarParams')
    # Compare only the firmware/VIN identity consumed by the current fingerprint
    # path. Historical input control settings never seed the verified cache.
    input_cp = next((message.carParams.to_dict()
                     for message in source_log.Event.read_multiple_bytes(decompress_stream(raw))
                     if message.which() == 'carParams'), None)
    # The pinned Rivian input predates the existing R1 name migration. Its
    # reference uses the current platform name; firmware and VIN remain exact.
    if segment == 'regen5FCAC896BBE|2025-04-08--23-13-35--0' and input_cp is not None:
      if input_cp.get('carFingerprint') == 'RIVIAN_R1_GEN1':
        input_cp['carFingerprint'] = 'RIVIAN_R1'
    identity = ('carFingerprint', 'carVin', 'carFw')
    if input_cp is None or any(input_cp[key] != source_cp[key] for key in identity):
      raise ValueError('Recording firmware/VIN identity differs from its published card reference')
    converted = car.CarParams.new_message(**source_cp)
    if converted.to_dict() != source_cp:
      raise ValueError('Replay CarParams source conversion changed typed values')
    sink = _Sink()
    put_cache(sink, 'CarParamsCache', converted, block=True)
    return {'CarParamsCache': sink.raw}
