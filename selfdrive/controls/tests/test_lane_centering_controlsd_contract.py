"""Source-contract: controlsd must gate LaneCentering on modelV2 all_checks.

SubMaster.valid only reflects msg.valid. Stale/low-freq modelV2 must also drop
the correction; all_checks = all_alive & all_freq_ok & all_valid.
"""

from pathlib import Path


_CTRLD = (Path(__file__).resolve().parents[1] / "controlsd.py").read_text(encoding="utf-8")


def test_controlsd_passes_modelv2_all_checks_to_lane_centering():
  # Integration expression must use freshness/frequency/validity, not payload valid alone.
  assert "self.sm.all_checks(['modelV2'])" in _CTRLD
  assert "self.sm.valid['modelV2']" not in _CTRLD


def test_controlsd_lane_centering_update_receives_bool_all_checks():
  # Call site must wrap the all_checks result in bool(...) for the model_valid arg.
  assert "bool(self.sm.all_checks(['modelV2']))" in _CTRLD
