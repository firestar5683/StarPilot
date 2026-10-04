import json

from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy, decode, to_value, read_saved


def test_unset_defaults_on_without_writing(tmp_path):
  class Source:
    def get_param_path(self, key):
      return str(tmp_path / key)
  source = Source()
  for _ in range(3):
    assert read_saved(source).policy.one_per_signal
  assert not list(tmp_path.iterdir())


def test_explicit_off_survives_document_roundtrip():
  policy = LaneChangePolicy(one_per_signal=False)
  raw = json.dumps(to_value(policy)).encode()
  for _ in range(3):
    saved = decode(raw)
    assert saved is not None and not saved.one_per_signal
    assert json.dumps(to_value(saved)).encode() == raw
