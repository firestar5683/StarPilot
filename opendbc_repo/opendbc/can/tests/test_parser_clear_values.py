import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.can.tests import TEST_DBC


class TestParserClearValues(unittest.TestCase):
  def test_empty_update_clears_every_list_without_replacing_aliases(self):
    parser = CANParser(TEST_DBC, [("CAN_FD_MESSAGE", 10)], 0)
    packer = CANPacker(TEST_DBC)
    first = packer.make_can_msg("CAN_FD_MESSAGE", 0, {"SIGNED": 12})
    second = packer.make_can_msg("CAN_FD_MESSAGE", 0, {"SIGNED": 34})
    parser.update([(1_000_000, [first]), (2_000_000, [second])])
    values = parser.vl_all["CAN_FD_MESSAGE"]
    self.assertIs(values, parser.vl_all[first[0]])
    self.assertEqual(values["SIGNED"], [12, 34])
    # Extra caller-created entries are also part of the public mapping.
    values["extra"] = [56]
    aliases = dict(values)
    timestamps = dict(parser.ts_nanos["CAN_FD_MESSAGE"])
    latest = dict(parser.vl["CAN_FD_MESSAGE"])

    self.assertEqual(parser.update([]), set())
    self.assertEqual(set(values), set(aliases))
    for key, value in aliases.items():
      self.assertIs(values[key], value)
      self.assertEqual(value, [])
    self.assertEqual(parser.ts_nanos["CAN_FD_MESSAGE"], timestamps)
    self.assertEqual(parser.vl["CAN_FD_MESSAGE"], latest)
    self.assertEqual(parser._last_update_nanos, 2_000_000)
    self.assertEqual(parser.last_nonempty_nanos, 2_000_000)

  def test_lazily_added_message_and_repeated_empty_updates(self):
    parser = CANParser(TEST_DBC, [], 0)
    parser.vl["Brake_Status"]
    values = parser.vl_all["Brake_Status"]
    values["Signal1"] = [1, 2]
    alias = values["Signal1"]
    for _ in range(3):
      self.assertEqual(parser.update([]), set())
      self.assertIs(values["Signal1"], alias)
      self.assertEqual(alias, [])
      alias.append(3)


if __name__ == "__main__":
  unittest.main()
