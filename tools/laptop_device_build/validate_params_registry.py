import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import tempfile


def tokens(text):
  pattern = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|R"([^ ()\\\t\r\n]{0,16})\(.*?\)\1"|"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|0x[0-9a-fA-F]+|\d+|.', re.S)
  return [match.group() for match in pattern.finditer(text) if not match.group().isspace() and not match.group().startswith(('//', '/*'))]


def string_value(value):
  if value.startswith('R"'):
    start = value.index('(')
    delimiter = value[2:start]
    return value[start + 1:-(len(delimiter) + 2)].encode()
  if not value.startswith('"'):
    raise ValueError(f'Unsupported C++ string: {value}')
  text = value[1:-1]
  output = bytearray()
  escapes = {'n': 10, 'r': 13, 't': 9, 'b': 8, 'f': 12, 'v': 11, 'a': 7, '\\': 92, '"': 34, "'": 39, '?': 63}
  index = 0
  while index < len(text):
    if text[index] != '\\':
      output.extend(text[index].encode())
      index += 1
      continue
    index += 1
    char = text[index]
    if char in escapes:
      output.append(escapes[char])
      index += 1
    elif char in '01234567':
      match = re.match(r'[0-7]{1,3}', text[index:])
      output.append(int(match.group(), 8))
      index += len(match.group())
    elif char == 'x':
      match = re.match(r'[0-9a-fA-F]+', text[index + 1:])
      if match is None:
        raise ValueError('Invalid hex escape')
      output.append(int(match.group(), 16))
      index += 1 + len(match.group())
    else:
      raise ValueError(f'Unsupported C++ escape: {char}')
  return bytes(output)


def expected_registry(header, params_header, schema):
  types_match = re.search(r'enum ParamKeyType\s*\{(.*?)\};', params_header, re.S)
  if types_match is None:
    raise ValueError('Missing ParamKeyType')
  types = {name: int(value) for name, value in re.findall(r'(\w+)\s*=\s*(\d+)', types_match.group(1))}
  body = tokens(header)
  start = body.index('keys')
  start = body.index('{', start)
  entries = []
  depth = 0
  begin = None
  for index in range(start + 1, len(body)):
    token = body[index]
    if token == '{':
      if depth == 0:
        begin = index
      depth += 1
    elif token == '}':
      if depth == 0:
        break
      depth -= 1
      if depth == 0:
        entries.append(body[begin:index + 1])
  result = {}
  for entry in entries:
    if len(entry) < 8 or entry[2:4] != [',', '{'] or entry[-2:] != ['}', '}']:
      raise ValueError(f'Unsupported registry entry: {entry}')
    key = string_value(entry[1]).decode()
    fields = []
    field = []
    nesting = 0
    for token in entry[4:-2]:
      if token in ('(', '{'):
        nesting += 1
      if token in (')', '}'):
        nesting -= 1
      if token == ',' and nesting == 0:
        fields.append(field)
        field = []
      else:
        field.append(token)
    fields.append(field)
    if len(fields) not in (2, 3) or len(fields[1]) != 1 or fields[1][0] not in types:
      raise ValueError(f'Unsupported attributes for {key}')
    default = None
    if len(fields) == 3:
      expression = fields[2]
      if all(token.startswith(('"', 'R"')) for token in expression):
        default = b''.join(string_value(token) for token in expression)
      else:
        value = ''.join(expression)
        match = re.fullmatch(r'std::to_string\(static_cast<int>\(cereal::(\w+)::(\w+)\)\)', value)
        if match is None:
          raise ValueError(f'Unsupported default for {key}: {value}')
        enum = re.search(r'enum\s+' + re.escape(match[1]) + r'\s*\{(.*?)\}', schema, re.S)
        ordinal = re.search(r'\b' + re.escape(match[2].lower()) + r'\s*@\s*(\d+)\s*;', enum.group(1)) if enum else None
        if ordinal is None:
          raise ValueError(f'Unresolved enum default for {key}')
        default = ordinal[1].encode()
    if key in result:
      raise ValueError(f'Duplicate registry key: {key}')
    result[key] = (types[fields[1][0]], default)
  if not result:
    raise ValueError('Empty registry')
  return result


class Buffer(ctypes.Structure):
  _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_size_t)]


class NativeRegistry:
  def __init__(self, library, directory):
    self.library = ctypes.CDLL(str(Path(library).resolve()))
    for name, arguments, returns in (
      ('params_create', [ctypes.c_char_p, ctypes.c_size_t], ctypes.c_void_p),
      ('params_destroy', [ctypes.c_void_p], None),
      ('params_last_error', [], ctypes.c_char_p),
      ('params_check_key', [ctypes.c_void_p, ctypes.c_char_p], ctypes.c_bool),
      ('params_get_key_type', [ctypes.c_void_p, ctypes.c_char_p], ctypes.c_int),
      ('params_get_default', [ctypes.c_void_p, ctypes.c_char_p], Buffer),
      ('params_keys_size', [ctypes.c_void_p], ctypes.c_size_t),
      ('params_key_at', [ctypes.c_void_p, ctypes.c_size_t], Buffer),
    ):
      function = getattr(self.library, name)
      function.argtypes = arguments
      function.restype = returns
    path = str(directory).encode()
    self.handle = self.library.params_create(path, len(path))
    self.check_error()
    if not self.handle:
      raise ValueError('Params constructor returned null')

  def check_error(self):
    error = self.library.params_last_error()
    if error:
      raise ValueError(error.decode(errors='replace'))

  def call(self, name, *args):
    value = getattr(self.library, name)(self.handle, *args)
    self.check_error()
    return value

  def read(self):
    result = {}
    for index in range(self.call('params_keys_size')):
      buffer = self.call('params_key_at', index)
      if not buffer.data:
        raise ValueError('Null key in native registry')
      key = ctypes.string_at(buffer.data, buffer.size)
      if not self.call('params_check_key', key):
        raise ValueError('Enumerated native key rejected')
      kind = self.call('params_get_key_type', key)
      buffer = self.call('params_get_default', key)
      default = ctypes.string_at(buffer.data, buffer.size) if buffer.data else None
      decoded = key.decode()
      if decoded in result:
        raise ValueError('Duplicate native key')
      result[decoded] = (kind, default)
    return result

  def close(self):
    self.library.params_destroy(self.handle)
    self.handle = None
    self.check_error()


def compare(expected, actual):
  missing = sorted(expected.keys() - actual.keys())
  extra = sorted(actual.keys() - expected.keys())
  wrong_type = sorted(key for key in expected.keys() & actual.keys() if expected[key][0] != actual[key][0])
  wrong_default = sorted(key for key in expected.keys() & actual.keys() if expected[key][1] != actual[key][1])
  if missing or extra or wrong_type or wrong_default:
    raise ValueError(json.dumps({'missing': missing, 'extra': extra, 'wrongType': wrong_type, 'wrongDefault': wrong_default}))


def validate(root):
  root = Path(root).resolve()
  paths = ['openpilot/common/params_keys.h', 'openpilot/common/params.h', 'openpilot/cereal/log.capnp', 'openpilot/common/libparams_c.so']
  expected = expected_registry(*((root / path).read_text() for path in paths[:3]))
  with tempfile.TemporaryDirectory(prefix='params-registry-build-') as directory:
    native = NativeRegistry(root / paths[3], directory)
    try:
      compare(expected, native.read())
    finally:
      native.close()
  return {'status': 'PASS', 'keys': len(expected), 'inputs': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}}


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('root', type=Path)
  parser.add_argument('--receipt', type=Path)
  arguments = parser.parse_args()
  receipt = validate(arguments.root)
  output = json.dumps(receipt, sort_keys=True)
  if arguments.receipt:
    arguments.receipt.write_text(output + '\n')
  print(output)
