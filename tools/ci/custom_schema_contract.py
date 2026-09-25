"""Check additive evolution of the custom messages already recorded by this fork.

The source-only schema policy protects upstream and historical reservations.
This separate native check protects the fields of the new populated slots,
including compiled offsets, types, defaults, union tags and enum meanings.
"""

from pathlib import Path
import json


CONTRACT = Path(__file__).with_name('custom-schema-contract.json')


def _children(schema, descriptor):
  kind = next(iter(descriptor))
  if kind == 'list':
    element = descriptor['list']['elementType']
    if next(iter(element)) in ('struct', 'enum', 'list'):
      yield from _children(schema.elementType, element)
  elif kind in ('struct', 'enum'):
    yield schema


def describe(module, roots):
  """Read the actual compiled layouts; source spelling alone is insufficient."""
  def resolve(name):
    value = module
    for part in name.split('.'):
      value = getattr(value, part)
    return value.schema

  pending = [resolve(name) for name in roots]
  result = {'roots': {name: str(resolve(name).node.id) for name in roots}, 'nodes': {}}
  while pending:
    schema = pending.pop()
    node = schema.node.to_dict()
    key = str(node['id'])
    if key in result['nodes']:
      continue
    if 'enum' in node:
      result['nodes'][key] = {'kind': 'enum', 'values': [e['name'] for e in node['enum']['enumerants']]}
      continue
    layout = node['struct']
    fields = {}
    for field in layout.get('fields', []):
      record = {k: v for k, v in field.items() if k not in ('codeOrder', 'annotations')}
      ordinal = str(field['ordinal'].get('explicit', 'group:' + field['name']))
      if 'group' in field:
        pending.append(schema.fields[field['name']].schema)
      else:
        record['slot'] = {k: v for k, v in field['slot'].items() if k != 'hadExplicitDefault'}
        descriptor = field['slot']['type']
        if next(iter(descriptor)) in ('struct', 'list', 'anyPointer'):
          # schema.Value stores these defaults as opaque pointers. Preserve the
          # value itself, including explicit pointer defaults, without expanding
          # it through the referenced type's potentially evolving field layout.
          value = schema.fields[field['name']].proto.slot.defaultValue
          record['slot']['defaultValue'] = {'schemaValueHex': value.as_builder().to_bytes().hex()}
        if next(iter(descriptor)) in ('struct', 'enum', 'list'):
          pending.extend(_children(schema.fields[field['name']].schema, descriptor))
      fields[ordinal] = record
    result['nodes'][key] = {'kind': 'struct', 'data_words': layout['dataWordCount'],
                            'pointers': layout['pointerCount'], 'is_group': layout['isGroup'],
                            'union_count': layout['discriminantCount'], 'union_offset': layout['discriminantOffset'],
                            'fields': fields}
  return result


def validate(current, baseline):
  """Allow new fields/types/enum values; retain existing wire and API meaning."""
  errors = []
  for name, type_id in baseline['roots'].items():
    if current['roots'].get(name) != type_id:
      errors.append(f'{name}: existing custom root renamed, removed or reassigned')
  for type_id, old in baseline['nodes'].items():
    new = current['nodes'].get(type_id)
    if new is None or new['kind'] != old['kind']:
      errors.append(f'{type_id}: existing referenced type removed or changed kind')
      continue
    if old['kind'] == 'enum':
      if new['values'][:len(old['values'])] != old['values']:
        errors.append(f'{type_id}: existing enum ordinals or names changed')
      continue
    if new['data_words'] < old['data_words'] or new['pointers'] < old['pointers'] or new['is_group'] != old['is_group']:
      errors.append(f'{type_id}: existing struct storage changed incompatibly')
    if old['union_count'] and (new['union_count'] < old['union_count'] or new['union_offset'] != old['union_offset']):
      errors.append(f'{type_id}: existing union layout changed')
    for ordinal, field in old['fields'].items():
      if new['fields'].get(ordinal) != field:
        errors.append(f'{type_id}.{field["name"]}: existing field @{ordinal} changed or removed')
  return errors


def main():
  from openpilot.cereal import custom

  baseline = json.loads(CONTRACT.read_text())
  errors = validate(describe(custom, baseline['roots']), baseline)
  print(json.dumps({'passed': not errors, 'errors': errors}, indent=2))
  return int(bool(errors))


if __name__ == '__main__':
  raise SystemExit(main())
