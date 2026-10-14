"""Toyota SecOC key decoding; never include credentials in diagnostics."""

import re


def decode_key(value):
  if isinstance(value, bytes):
    try:
      value = value.decode('ascii')
    except UnicodeDecodeError:
      return None
  if type(value) is not str:
    return None
  value = value.strip()
  if re.fullmatch(r'[0-9a-fA-F]{32}', value) is None:
    return None
  return bytes.fromhex(value)
