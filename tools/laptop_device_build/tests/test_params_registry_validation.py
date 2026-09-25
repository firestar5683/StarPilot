import unittest

from tools.laptop_device_build.validate_params_registry import compare, expected_registry


class TestParamsRegistryValidation(unittest.TestCase):
  def registry(self):
    return expected_registry('''inline static auto keys = {
      {"Plain", {PERSISTENT, STRING}},
      {"Empty", {PERSISTENT, STRING, ""}},
      {"Escaped", {PERSISTENT, STRING, "a\\n\\\"b"}},
      {"Raw", {PERSISTENT, JSON, R"tag({"a":[1,2]})tag"}},
      {"Enum", {PERSISTENT, INT, std::to_string(static_cast<int>(cereal::Mode::STANDARD))}},
    };''', 'enum ParamKeyType { STRING = 0, INT = 2, JSON = 5 };', 'enum Mode { standard @1; }')

  def test_cpp_literals_and_absent_default_are_distinct(self):
    self.assertEqual(self.registry(), {'Plain': (0, None), 'Empty': (0, b''),
                                     'Escaped': (0, b'a\n"b'), 'Raw': (5, b'{"a":[1,2]}'), 'Enum': (2, b'1')})

  def test_stale_missing_extra_type_and_default_rejected(self):
    expected = self.registry()
    compare(expected, dict(expected))
    for change in ('missing', 'extra', 'type', 'default'):
      with self.subTest(change=change):
        actual = dict(expected)
        if change == 'missing':
          del actual['Raw']
        elif change == 'extra':
          actual['OldKey'] = (0, None)
        elif change == 'type':
          actual['Enum'] = (0, b'1')
        else:
          actual['Empty'] = (0, None)
        with self.assertRaises(ValueError):
          compare(expected, actual)

  def test_unknown_expression_and_duplicate_fail_closed(self):
    for header in ('auto keys={{"A",{PERSISTENT,STRING,make_default()}}};',
                   'auto keys={{"A",{PERSISTENT,STRING}},{"A",{PERSISTENT,STRING}}};'):
      with self.assertRaises(ValueError):
        expected_registry(header, 'enum ParamKeyType { STRING = 0 };', '')


if __name__ == '__main__':
  unittest.main()
