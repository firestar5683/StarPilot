import random
import unittest

from openpilot.starpilot.flm.fullrate_collector import identity


class TestIdentity(unittest.TestCase):
  def test_exact_lowercase_hex_language(self):
    allowed = '0123456789abcdef'
    base = 'a' * 64
    for code in range(256):
      character = chr(code)
      for position in range(64):
        value = base[:position] + character + base[position + 1:]
        self.assertIs(identity(value), character in allowed)
    randomizer = random.Random(64)
    for _ in range(1000):
      self.assertIs(identity(''.join(randomizer.choice(allowed) for _ in range(64))), True)

  def test_strict_types_lengths_and_unicode(self):
    class StringSubclass(str):
      pass
    for value in (None, False, 0, b'a' * 64, bytearray(b'a' * 64), StringSubclass('a' * 64)):
      self.assertIs(identity(value), False)
    for length in (0, 1, 63, 65, 10000):
      self.assertIs(identity('a' * length), False)
    for character in ('\n', '\0', 'é', 'Ａ', '𝟢', '٠', '\ud800'):
      self.assertIs(identity('a' * 63 + character), False)
