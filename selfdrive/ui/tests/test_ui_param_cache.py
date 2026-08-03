import unittest

from openpilot.selfdrive.ui.lib.ui_param_cache import UIParamCache


class FakeParams:
  def __init__(self):
    self.values = {"enabled": False, "count": 1}
    self.calls = []

  def get(self, key, **_kwargs):
    self.calls.append(("get", key))
    return self.values.get(key)

  def get_bool(self, key, **_kwargs):
    self.calls.append(("get_bool", key))
    return bool(self.values.get(key, False))

  def get_int(self, key, **_kwargs):
    self.calls.append(("get_int", key))
    return int(self.values.get(key, 0))

  def get_float(self, key, **_kwargs):
    self.calls.append(("get_float", key))
    return float(self.values.get(key, 0.0))

  def put(self, key, value, **_kwargs):
    self.values[key] = value

  def put_bool(self, key, value, **_kwargs):
    self.values[key] = value

  def put_int(self, key, value, **_kwargs):
    self.values[key] = value

  def put_float(self, key, value, **_kwargs):
    self.values[key] = value

  def put_nonblocking(self, key, value):
    self.values[key] = value

  def put_bool_nonblocking(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)

  def clear_all(self, marker=None):
    self.calls.append(("clear_all", marker))
    self.values.clear()


class TestUIParamCache(unittest.TestCase):
  def test_reads_are_shared_until_ttl(self):
    now = [0.0]
    params = FakeParams()
    cached = UIParamCache(params, ttl=0.1, clock=lambda: now[0])

    self.assertFalse(cached.get_bool("enabled"))
    self.assertFalse(cached.get_bool("enabled"))
    self.assertEqual(params.calls, [("get_bool", "enabled")])

    now[0] = 0.11
    params.values["enabled"] = True
    self.assertTrue(cached.get_bool("enabled"))
    self.assertEqual(params.calls.count(("get_bool", "enabled")), 2)

  def test_writes_invalidate_immediately(self):
    params = FakeParams()
    cached = UIParamCache(params, ttl=10.0)

    self.assertFalse(cached.get_bool("enabled"))
    cached.put_bool("enabled", True)
    self.assertTrue(cached.get_bool("enabled"))
    self.assertEqual(params.calls.count(("get_bool", "enabled")), 2)

  def test_zero_ttl_disables_caching(self):
    params = FakeParams()
    cached = UIParamCache(params, ttl=0.0)

    self.assertFalse(cached.get_bool("enabled"))
    params.values["enabled"] = True
    self.assertTrue(cached.get_bool("enabled"))
    self.assertEqual(params.calls.count(("get_bool", "enabled")), 2)

  def test_all_write_paths_invalidate(self):
    operations = (
      lambda cache: cache.put("enabled", True),
      lambda cache: cache.put_bool("enabled", True),
      lambda cache: cache.put_int("enabled", 1),
      lambda cache: cache.put_float("enabled", 1.0),
      lambda cache: cache.put_nonblocking("enabled", True),
      lambda cache: cache.put_bool_nonblocking("enabled", True),
    )
    for operation_index, operation in enumerate(operations):
      with self.subTest(operation_index=operation_index):
        params = FakeParams()
        cached = UIParamCache(params, ttl=10.0)
        self.assertFalse(cached.get_bool("enabled"))
        operation(cached)
        self.assertTrue(cached.get_bool("enabled"))
        self.assertEqual(params.calls.count(("get_bool", "enabled")), 2)

  def test_remove_and_clear_all_invalidate(self):
    params = FakeParams()
    cached = UIParamCache(params, ttl=10.0)

    self.assertTrue(cached.get_int("count"))
    cached.remove("count")
    self.assertEqual(cached.get_int("count"), 0)

    self.assertFalse(cached.get_bool("enabled"))
    params.values["enabled"] = True
    cached.clear_all("flag")
    params.values["enabled"] = True
    self.assertTrue(cached.get_bool("enabled"))
    self.assertIn(("clear_all", "flag"), params.calls)


if __name__ == "__main__":
  unittest.main()
