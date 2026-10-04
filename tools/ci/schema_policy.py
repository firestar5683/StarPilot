#!/usr/bin/env python3
"""Enforce cereal's reserved-event contract against the pinned upstream schemas.

See openpilot/cereal/README.md, Custom forks. When syncing upstream, review and
update schema-policy.json alongside upstream-sync.json. Custom fields belong
inside reserved custom.capnp structs; log.capnp may rename only their event
aliases and the reserved raw-data aliases, preserving ordinals and type IDs.
"""

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
POLICY = Path(__file__).with_name('schema-policy.json')
DECLARATION = re.compile(r'^struct (\w+) @(0x[0-9a-fA-F]+)\s*\{', re.MULTILINE)
SCHEMA_ROOTS = ('openpilot/cereal', 'opendbc_repo/opendbc/car')


def sha256(data):
  return hashlib.sha256(data).hexdigest()


def custom_structs(source):
  # Mask comments and strings before counting braces; quoted defaults may
  # contain braces without ending a message definition.
  masked = re.sub(r'"(?:\\.|[^"\\])*"|\#[^\n]*', lambda m: ' ' * len(m[0]), source)
  definitions, bodies, spans = {}, {}, []
  cursor = 0
  for match in DECLARATION.finditer(masked):
    if match.start() < cursor:
      continue
    depth, end = 1, match.end()
    while depth and end < len(masked):
      depth += (masked[end] == '{') - (masked[end] == '}')
      end += 1
    if depth:
      raise ValueError('Unclosed custom struct')
    name, type_id = match.groups()
    if type_id.lower() in definitions or name in definitions.values():
      raise ValueError('Duplicate custom type ID or name')
    definitions[type_id.lower()] = name
    bodies[type_id.lower()] = source[match.end():end - 1]
    spans.append((match.start(), end))
    cursor = end
  remainder = source
  for start, end in reversed(spans):
    remainder = remainder[:start] + remainder[end:]
  return definitions, bodies, remainder


def validate(schemas, policy, sync):
  errors = []
  expected_paths = {*policy['unchanged_schemas'], 'openpilot/cereal/custom.capnp', 'openpilot/cereal/log.capnp'}
  for path in sorted(set(schemas) - expected_paths):
    errors.append(f'{path}: schema has no explicit policy coverage')
  for path in sorted(expected_paths - set(schemas)):
    errors.append(f'{path}: policy-covered schema is missing')
  if expected_paths - set(schemas):
    return errors
  dependencies = {entry['path']: entry['commit'] for entry in sync['dependencies']}
  if sync['upstream']['commit'] != policy['upstream_commit'] or dependencies.get('opendbc_repo') != policy['opendbc_commit']:
    errors.append('Schema policy must be reviewed against the current upstream sync pins')
  for path, expected in policy['unchanged_schemas'].items():
    reviewed = policy.get('reviewed_enum_additions', {}).get(path)
    candidate = schemas[path]
    if reviewed:
      source = candidate.decode()
      pattern = rf'(enum {re.escape(reviewed["enum"])}\s*\{{)([^}}]*)(\}})'
      match = re.search(pattern, source)
      field = reviewed['field']
      if match is None or len(re.findall(rf'(?m)^\s*{re.escape(field)}\s*$', match[2])) != 1:
        errors.append(f'{path}: reviewed enum addition is missing or changed')
      else:
        body = re.sub(rf'(?m)^[ \t]*{re.escape(field)}[ \t]*\n', '', match[2])
        source = source[:match.start(2)] + body + source[match.end(2):]
        candidate = source.encode()
    if sha256(candidate) != expected:
      errors.append(f'{path}: upstream-owned schema changed; use custom.capnp reserved structs')
  try:
    definitions, bodies, remainder = custom_structs(schemas['openpilot/cereal/custom.capnp'].decode())
  except (UnicodeDecodeError, ValueError) as error:
    return [*errors, f'custom.capnp: {error}']
  expected_ids = {slot['type_id'] for slot in policy['reserved']}
  if set(definitions) != expected_ids:
    errors.append('custom.capnp: reserved type IDs were removed/changed or unreserved top-level types were added')
  reserved_by_name = {slot['struct']: slot for slot in policy['reserved']}
  for index in policy['historical_empty_slots']:
    original_name = f'CustomReserved{index}'
    type_id = reserved_by_name[original_name]['type_id']
    body = re.sub(r'#[^\n]*', '', bodies.get(type_id, ''))
    if definitions.get(type_id) != original_name or body.strip():
      errors.append(f'custom.capnp: historical slot {index} must retain its original name and empty body')
  for index, restored in policy.get('historical_restored', {}).items():
    type_id = restored['type_id']
    body = re.sub(r'#[^\n]*', '', bodies.get(type_id, ''))
    field = restored['field']
    if not re.search(rf'(?m)^\s*{re.escape(field)}\s*$', body):
      errors.append(f'custom.capnp: historical slot {index} must preserve {field}')
    slot = next((entry for entry in policy['reserved'] if entry['type_id'] == type_id), None)
    if slot is None or slot['ordinal'] != restored['ordinal']:
      errors.append(f'custom.capnp: historical slot {index} type ID or event ordinal changed')
  def canonical(text):
    return re.sub(r'\s+', '', re.sub(r'#[^\n]*', '', text))

  for restored in policy.get('historical_prefixes', {}).values():
    if (definitions.get(restored['type_id']) != restored['name'] or
        not canonical(bodies.get(restored['type_id'], '')).startswith(canonical(restored['body']))):
      errors.append('custom.capnp: historical occupied prefix changed')
  if remainder.strip() != policy['custom_header'].strip():
    errors.append('custom.capnp: edits outside the reserved structs')
  log = schemas['openpilot/cereal/log.capnp'].decode()
  for slot in policy['reserved']:
    name = definitions.get(slot['type_id'])
    if name is None:
      continue
    # Changing the name is permitted; changing its type or ordinal is not.
    pattern = rf'(?m)^(\s*)\w+ @{slot["ordinal"]} :Custom\.{re.escape(name)};'
    log, count = re.subn(pattern, rf'\g<1>{slot["field"]} @{slot["ordinal"]} :Custom.{slot["struct"]};', log)
    if count != 1:
      errors.append(f'log.capnp: reserved event @{slot["ordinal"]} no longer points to its original custom type ID')
  for ordinal, name in policy['raw_reserved'].items():
    log, count = re.subn(rf'(?m)^(\s*)\w+ @{ordinal} :Data;', rf'\g<1>{name} @{ordinal} :Data;', log)
    if count != 1:
      errors.append(f'log.capnp: reserved raw event @{ordinal} changed type or ordinal')
  for reviewed in policy.get('reviewed_log_additions', []):
    pattern = rf'({re.escape(reviewed["scope"])}(?:\s+@0x[0-9a-fA-F]+)?\s*\{{)([^}}]*)(\}})'
    match = re.search(pattern, log)
    if match is None:
      errors.append('log.capnp: reviewed addition scope missing')
      continue
    body = match[2]
    for field in reviewed['fields']:
      body, count = re.subn(rf'(?m)^[ \t]*{re.escape(field)}[ \t]*\n', '', body)
      if count != 1:
        errors.append('log.capnp: reviewed addition missing or changed')
    log = log[:match.start(2)] + body + log[match.end(2):]
  if sha256(log.encode()) != policy['log_sha256']:
    errors.append('log.capnp: changes outside the permitted reserved-event aliases')
  return errors


def read_inputs(root=ROOT):
  policy = json.loads(POLICY.read_text())
  paths = {path.relative_to(root).as_posix() for schema_root in SCHEMA_ROOTS for path in (root / schema_root).rglob('*.capnp')}
  return {path: (root / path).read_bytes() for path in paths}, policy, json.loads((root / 'upstream-sync.json').read_text())


def main():
  errors = validate(*read_inputs())
  print(json.dumps({'passed': not errors, 'errors': errors}, indent=2))
  return int(bool(errors))


if __name__ == '__main__':
  raise SystemExit(main())
