"""SLC native offset actions and both unit paths against real temporary Params."""

from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any, cast
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.speed_limits import offset_document as od
from openpilot.starpilot.speed_limits.runtime_settings import read_params
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest, row_change
from openpilot.starpilot.ui.slc_offset_feature import DOCUMENT_KEY, SlcOffsetOwner, native_parked


class SlcOffsetFeatureTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.cp: NS | None = NS(carFingerprint="TOYOTA_COROLLA_TSS2", openpilotLongitudinalControl=True, pcmCruise=False,
                 notCar=False, dashcamOnly=False, passive=False)
    self.owner = FeatureSettingsOwner(self.params, lambda _group: self.parked,
                                      vehicle_fingerprint=lambda: self.cp.carFingerprint if self.cp else None,
                                      vehicle_params=lambda: self.cp)
    self.units = SlcOffsetOwner(self.params, lambda: self.parked, lambda: self.cp)

  def raw(self, key):
    path = Path(self.params.get_param_path(key))
    return path.read_bytes() if path.exists() else None

  def row(self, key):
    state = self.owner.snapshot("slc", parked=self.parked, system_long=True, lateral_context=True, metric=False)
    return next(item for item in state.rows if item.key == key)

  @staticmethod
  def confirm(row):
    return FeatureSettingsRequest(row.key, row.source, "confirm", confirmation=True,
                                  related_source=row.related_source, vehicle_fingerprint=row.vehicle_fingerprint,
                                  capability=row.capability, dependencies=row.dependencies)

  def test_native_offroad_uses_retained_fresh_authority_adapter(self):
    ui = NS()
    with patch("openpilot.starpilot.ui.runtime_snapshot.RuntimeSnapshotAdapter") as factory:
      factory.return_value.confirmed_offroad.side_effect = [True, False]
      self.assertTrue(native_parked(ui))
      self.assertFalse(native_parked(ui))
      factory.assert_called_once_with(ui)

  def test_pcm_cruise_longitudinal_can_adopt_and_enable_slc(self):
    assert self.cp is not None
    self.cp.carFingerprint = "TOYOTA_HIGHLANDER_TSS2"
    self.cp.pcmCruise = True
    state = self.owner.snapshot("slc", parked=True, system_long=False, lateral_context=True, metric=False)
    adopt = next(row for row in state.rows if row.key == "slc_adopt")
    self.assertTrue(adopt.available)
    self.assertTrue(self.owner.apply(self.confirm(adopt)))
    row = self.row("SpeedLimitController")
    self.assertTrue(row.available)
    request = row_change(row)
    assert request is not None
    self.assertTrue(self.owner.apply(request))
    self.cp.openpilotLongitudinalControl = False
    self.assertFalse(self.row("SpeedLimitController").available)

  def test_explicit_adopt_edit_and_global_units_preserve_exact_si(self):
    self.params.put_bool("IsMetric", False, block=True)
    self.params.put("Offset1", 5.0, block=True)
    self.params.put("Offset7", -2.0, block=True)
    old = (self.raw("Offset1"), self.raw("Offset7"))
    before = read_params(self.params).offsets
    self.assertFalse(self.row("SpeedLimitController").available)
    adopt = self.row("slc_adopt")
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(adopt.key, adopt.source, "confirm",
                                                              vehicle_fingerprint=adopt.vehicle_fingerprint,
                                                              capability=adopt.capability, dependencies=adopt.dependencies)))
    self.assertTrue(self.owner.apply(self.confirm(adopt)))
    self.assertTrue(self.row("SpeedLimitController").available)
    self.assertEqual(read_params(self.params).offsets, before)
    self.assertEqual((self.raw("Offset1"), self.raw("Offset7")), old)

    first = self.row("Offset1")
    self.assertTrue(first.available)
    self.assertEqual(row_change(first).direction, 1)
    first_edit = row_change(first)
    assert first_edit is not None
    self.assertTrue(self.owner.apply(first_edit))
    document = od.decode(self.raw(DOCUMENT_KEY))
    self.assertAlmostEqual(document.offsets_mps[0], 6 * od.MPH_TO_MPS)
    self.assertEqual(document.schedule().bands[-1].offset_mps, 0.0)
    self.assertTrue(self.units.change_units(True, b"0"))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), document)
    metric_row = self.row("Offset1")
    self.assertIn("km/h", metric_row.label)
    metric_edit = row_change(metric_row)
    assert metric_edit is not None
    self.assertTrue(self.owner.apply(metric_edit))
    adjusted = od.decode(self.raw(DOCUMENT_KEY))
    self.assertAlmostEqual(adjusted.offsets_mps[0] - document.offsets_mps[0], od.KPH_TO_MPS)
    self.assertTrue(self.units.change_units(False, b"1"))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), adjusted)
    self.assertEqual((self.raw("Offset1"), self.raw("Offset7")), old)

  def test_rounded_range_labels_do_not_rewrite_si_bounds(self):
    document = od.OffsetDocument(od.IMPERIAL_BOUNDS, (0.0,) * 7)
    self.params.put(DOCUMENT_KEY, od.to_value(document), block=True)
    original = self.raw(DOCUMENT_KEY)
    rows = [self.row(f"Offset{index}").label for index in range(1, 8)]
    self.assertEqual(rows, [f"{low}–{high} mph offset" for low, high in
                           ((0, 25), (25, 35), (35, 45), (45, 55), (55, 65), (65, 75), (75, 100))])
    self.assertEqual(self.raw(DOCUMENT_KEY), original)
    self.assertTrue(self.units.change_units(True, None))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), document)

  def test_onroad_adopted_offsets_edit_without_repair_authority(self):
    self.params.put_bool("IsMetric", False, block=True)
    document = od.OffsetDocument(od.IMPERIAL_BOUNDS, (0.0,) * 7)
    self.params.put(DOCUMENT_KEY, od.to_value(document), block=True)
    owner = FeatureSettingsOwner(self.params, lambda group: group != "parked_preferences",
                                 vehicle_fingerprint=lambda: self.cp.carFingerprint if self.cp else None,
                                 vehicle_params=lambda: self.cp)
    state = owner.snapshot("slc", parked=False, system_long=True, lateral_context=True, metric=False,
                           configure_while_driving=True)
    offset = next(row for row in state.rows if row.key == "Offset2")
    reset = next(row for row in state.rows if row.key == "slc_reset")
    self.assertTrue(offset.available)
    self.assertFalse(reset.available)
    request = row_change(offset)
    assert request is not None
    self.assertTrue(owner.apply(request))
    self.assertFalse(owner.apply(self.confirm(reset)))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).offsets_mps[1], od.MPH_TO_MPS)
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(owner.apply(request))

  def test_off_and_display_only_corrupt_legacy_allow_unit_change(self):
    Path(self.params.get_param_path("Offset1")).write_bytes(b"nan")
    Path(self.params.get_param_path("IsMetric")).write_bytes(b"bad")
    self.params.put_bool("ShowSpeedLimits", True, block=True)
    self.cp = None  # global display setting cannot require a supported car when SLC is off
    self.parked = False
    self.assertTrue(self.units.change_units(True, b"bad"))
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    self.assertEqual(self.raw("Offset1"), b"nan")
    self.assertEqual(self.raw("IsMetric"), b"1")

  def test_valid_legacy_unit_migration_waits_for_park_even_with_slc_off(self):
    self.params.put_bool("IsMetric", False, block=True)
    self.params.put("Offset1", 5.0, block=True)
    self.params.put_bool("SpeedLimitController", False, block=True)
    self.parked = False
    self.assertFalse(self.units.change_units(True, b"0"))
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    self.assertEqual(self.raw("IsMetric"), b"0")

  def test_saved_on_corrupt_legacy_writes_marker_before_unit(self):
    self.params.put_bool("SpeedLimitController", True, block=True)
    Path(self.params.get_param_path("Offset3")).write_bytes(b"bad")
    self.assertTrue(self.units.change_units(True, None))
    self.assertIs(od.decode(self.raw(DOCUMENT_KEY)), od.NEEDS_REVIEW)
    self.assertEqual(self.raw("IsMetric"), b"1")
    self.assertFalse(read_params(self.params).enabled)
    reset = self.row("slc_reset")
    self.assertTrue(self.owner.apply(self.confirm(reset)))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).offsets_mps, (0.0,) * 7)
    self.assertTrue(read_params(self.params).enabled)
    self.assertEqual(self.raw("Offset3"), b"bad")

  def test_marker_failure_veto_and_stale_source_recheck(self):
    self.params.put_bool("SpeedLimitController", True, block=True)
    Path(self.params.get_param_path("Offset1")).write_bytes(b"bad")
    original = self.params.put

    def fails_marker(key, value, block=False):
      if key == DOCUMENT_KEY:
        raise OSError("write failed")
      return original(key, value, block=block)

    with patch.object(self.params, "put", side_effect=fails_marker):
      self.assertFalse(self.units.change_units(True, None))
    self.assertIsNone(self.raw("IsMetric"))
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    Path(self.params.get_param_path("Offset1")).write_bytes(b"1")
    adopt = self.row("slc_adopt")
    Path(self.params.get_param_path("Offset1")).write_bytes(b"2")
    self.assertFalse(self.owner.apply(self.confirm(adopt)))
    self.assertIsNone(self.raw(DOCUMENT_KEY))

  def test_absent_corrupt_legacy_reset_recovers_without_changing_saved_switch(self):
    for saved_on in (False, True):
      with self.subTest(saved_on=saved_on):
        if saved_on:
          self.params.put_bool("SpeedLimitController", True, block=True)
        Path(self.params.get_param_path("Offset1")).write_bytes(b"bad")
        self.assertFalse(read_params(self.params).enabled)
        reset = self.row("slc_reset")
        self.assertTrue(reset.available)
        self.assertIsNone(reset.source)
        self.assertFalse(self.owner.apply(FeatureSettingsRequest("slc_reset", None, "confirm",
                                                                 confirmation=False, related_source=reset.related_source,
                                                                 capability=reset.capability, dependencies=reset.dependencies)))
        self.assertTrue(self.owner.apply(self.confirm(reset)))
        document = od.decode(self.raw(DOCUMENT_KEY))
        self.assertEqual(document, od.adopt_legacy(False, (0.0,) * 7))
        self.assertEqual(self.raw("Offset1"), b"bad")
        self.assertEqual(self.raw("SpeedLimitController"), b"1" if saved_on else None)
        self.assertEqual(read_params(self.params).enabled, saved_on)
        Path(self.params.get_param_path(DOCUMENT_KEY)).unlink()

  def test_absent_corrupt_reset_rechecks_legacy_and_waits_for_valid_units(self):
    legacy = Path(self.params.get_param_path("Offset4"))
    legacy.write_bytes(b"bad")
    reset = self.row("slc_reset")
    legacy.write_bytes(b"different bad")
    self.assertFalse(self.owner.apply(self.confirm(reset)))
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    Path(self.params.get_param_path("IsMetric")).write_bytes(b"invalid")
    self.assertFalse(self.row("slc_reset").available)
    self.assertFalse(self.owner.apply(self.confirm(self.row("slc_reset"))))
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    self.assertTrue(self.units.change_units(True, b"invalid"))
    self.assertTrue(self.row("slc_reset").available)
    self.assertTrue(self.owner.apply(self.confirm(self.row("slc_reset"))))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).bounds_mps, od.METRIC_BOUNDS)

  def test_saved_off_corrupt_unit_change_rechecks_legacy_before_unit_write(self):
    legacy = Path(self.params.get_param_path("Offset1"))
    legacy.write_bytes(b"bad")
    original = self.units._same_unit_source

    def mutate_at_final_guard(snap, capability):
      legacy.write_bytes(b"changed")
      return original(snap, capability)

    with patch.object(self.units, "_same_unit_source", side_effect=mutate_at_final_guard):
      self.assertFalse(self.units.change_units(True, None))
    self.assertIsNone(self.raw("IsMetric"))
    self.assertIsNone(self.raw(DOCUMENT_KEY))

  def test_stale_unit_capability_and_parked_edit_write_nothing(self):
    self.assertTrue(self.owner.apply(self.confirm(self.row("slc_adopt"))))
    edit = row_change(self.row("Offset2"))
    assert edit is not None
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.owner.apply(edit))
    self.params.put_bool("IsMetric", False, block=True)
    assert self.cp is not None
    self.cp.carFingerprint = "TOYOTA_CAMRY"
    self.assertFalse(self.owner.apply(edit))
    self.cp.carFingerprint = "TOYOTA_COROLLA_TSS2"
    self.parked = False
    self.assertFalse(self.owner.apply(edit))

  def test_valid_document_ignores_legacy_bytes_and_reset_keeps_bounds(self):
    self.assertTrue(self.owner.apply(self.confirm(self.row("slc_adopt"))))
    original = od.decode(self.raw(DOCUMENT_KEY))
    Path(self.params.get_param_path("Offset1")).write_bytes(b"bad")
    self.assertTrue(self.units.change_units(True, None))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), original)
    reset = self.row("slc_reset")
    self.assertTrue(self.owner.apply(self.confirm(reset)))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).bounds_mps, original.bounds_mps)

  def test_unit_write_failure_after_adoption_keeps_original_unit_and_si_schedule(self):
    self.params.put_bool("SpeedLimitController", True, block=True)
    self.params.put("Offset2", 3.0, block=True)
    expected = od.adopt_legacy(False, (0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    with patch.object(self.params, "put_bool", side_effect=OSError("unit write failed")):
      self.assertFalse(self.units.change_units(True, None))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), expected)
    self.assertIsNone(self.raw("IsMetric"))
    self.assertEqual(self.raw("Offset2"), b"3.0")

  def test_corrupt_document_and_units_require_explicit_repairs(self):
    self.params.put_bool("SpeedLimitController", True, block=True)
    Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(b"{broken")
    Path(self.params.get_param_path("IsMetric")).write_bytes(b"broken")
    self.assertTrue(self.units.change_units(True, b"broken"))
    self.assertEqual(self.raw(DOCUMENT_KEY), b"{broken")
    self.assertFalse(read_params(self.params).enabled)
    reset = self.row("slc_reset")
    self.assertTrue(self.owner.apply(self.confirm(reset)))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).offsets_mps, (0.0,) * 7)
    self.assertTrue(read_params(self.params).enabled)

  def test_all_seven_edits_and_stale_unit_request(self):
    self.assertTrue(self.owner.apply(self.confirm(self.row("slc_adopt"))))
    for index in range(1, 8):
      row = self.row(f"Offset{index}")
      edit = row_change(row, -1)
      assert edit is not None
      self.assertTrue(self.owner.apply(edit))
    document = od.decode(self.raw(DOCUMENT_KEY))
    self.assertEqual(document.offsets_mps, (-od.MPH_TO_MPS,) * 7)
    self.assertEqual(document.schedule().bands[-1].offset_mps, 0.0)
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.units.change_units(False, None))
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), document)

  def test_large_and_compact_metric_callbacks_use_same_owner_and_restore_veto(self):
    from openpilot.selfdrive.ui.layouts.settings.toggles import TogglesLayout
    from openpilot.selfdrive.ui.mici.layouts.settings import toggles as compact

    large = TogglesLayout.__new__(TogglesLayout)
    large._params = self.params
    large._slc_offsets = self.units
    large._metric_source = None
    large._toggles = {"IsMetric": NS(action_item=NS(set_state=lambda value: setattr(large, "shown", value)))}
    large._toggle_defs = {"IsMetric": (lambda: "metric", "", "", False)}
    self.assertTrue(large._toggle_callback(True, "IsMetric"))
    self.assertTrue(large.shown)
    self.assertEqual(self.raw("IsMetric"), b"1")
    adopted = od.decode(self.raw(DOCUMENT_KEY))

    compact_layout = compact.TogglesLayoutMici.__new__(compact.TogglesLayoutMici)
    compact_layout._slc_offsets = self.units
    compact_layout._metric_source = b"0"  # stale displayed source
    cast(Any, compact_layout)._metric_toggle = NS(set_checked=lambda value: setattr(compact_layout, "shown", value))
    with patch.object(compact, "ui_state", NS(params=self.params)):
      compact_layout._on_metric(False)
      self.assertTrue(compact_layout.shown)
      self.assertEqual(self.raw("IsMetric"), b"1")
      compact_layout._metric_source = b"1"
      compact_layout._on_metric(False)
      self.assertFalse(compact_layout.shown)
    self.assertEqual(self.raw("IsMetric"), b"0")
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)), adopted)

  def test_both_native_adapters_confirm_adoption_with_displayed_unit_source(self):
    from openpilot.starpilot.ui import feature_settings_compact as compact
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.system.ui.widgets import DialogResult

    class Dialog:
      def __init__(self, _question, *_args, callback=None, **_kwargs):
        self.confirmed = callback or _args[-1]

    self.params.put_bool("IsMetric", True, block=True)
    row = self.row("slc_adopt")
    large = StarShellSession.__new__(StarShellSession)
    cast(Any, large).feature_request = self.owner.apply
    pushed = []
    with patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog", Dialog), \
         patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget", pushed.append):
      large._confirm_feature_reset(row)
      pushed[-1].confirmed(DialogResult.CONFIRM)
    self.assertIsInstance(od.decode(self.raw(DOCUMENT_KEY)), od.OffsetDocument)

    Path(self.params.get_param_path(DOCUMENT_KEY)).unlink()
    row = self.row("slc_adopt")
    compact_adapter = compact.FeatureSettingsCompact(cast(Any, NS(feature_request=self.owner.apply)))
    pushed = []
    with patch.object(compact, "BigConfirmationDialog", Dialog), \
         patch.object(compact.gui_app, "push_widget", pushed.append), \
         patch.object(compact.gui_app, "texture", lambda *_args: None):
      compact_adapter._confirm_reset(row, lambda: None)
      pushed[-1].confirmed()
    self.assertIsInstance(od.decode(self.raw(DOCUMENT_KEY)), od.OffsetDocument)

  def test_both_native_reset_confirmations_recover_corrupt_legacy_and_recheck_source(self):
    from openpilot.starpilot.ui import feature_settings_compact as compact
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.system.ui.widgets import DialogResult

    class Dialog:
      def __init__(self, _question, *_args, callback=None, **_kwargs):
        self.confirmed = callback or _args[-1]

    legacy = Path(self.params.get_param_path("Offset1"))
    legacy.write_bytes(b"bad")
    large = StarShellSession.__new__(StarShellSession)
    cast(Any, large).feature_request = self.owner.apply
    pushed = []
    with patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog", Dialog), \
         patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget", pushed.append):
      large._confirm_feature_reset(self.row("slc_reset"))
      legacy.write_bytes(b"changed")
      pushed[-1].confirmed(DialogResult.CONFIRM)
      self.assertIsNone(self.raw(DOCUMENT_KEY))
      large._confirm_feature_reset(self.row("slc_reset"))
      pushed[-1].confirmed(DialogResult.CONFIRM)
    self.assertFalse(read_params(self.params).enabled)
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).offsets_mps, (0.0,) * 7)
    Path(self.params.get_param_path(DOCUMENT_KEY)).unlink()

    self.params.put_bool("SpeedLimitController", True, block=True)
    compact_adapter = compact.FeatureSettingsCompact(cast(Any, NS(feature_request=self.owner.apply)))
    pushed = []
    with patch.object(compact, "BigConfirmationDialog", Dialog), \
         patch.object(compact.gui_app, "push_widget", pushed.append), \
         patch.object(compact.gui_app, "texture", lambda *_args: None):
      compact_adapter._confirm_reset(self.row("slc_reset"), lambda: None)
      pushed[-1].confirmed()
    self.assertTrue(read_params(self.params).enabled)
    self.assertEqual(self.raw("SpeedLimitController"), b"1")
    self.assertEqual(od.decode(self.raw(DOCUMENT_KEY)).offsets_mps, (0.0,) * 7)

  def test_both_native_reset_dialogs_describe_saved_or_default_ranges(self):
    from openpilot.starpilot.ui import feature_settings_compact as compact
    from openpilot.starpilot.ui.runtime_app import StarShellSession

    class Dialog:
      def __init__(self, question, *_args, **_kwargs):
        self.question = question

    large = StarShellSession.__new__(StarShellSession)
    compact_adapter = compact.FeatureSettingsCompact(cast(Any, NS(feature_request=self.owner.apply)))
    pushed = []
    with patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog", Dialog), \
         patch.object(compact, "BigConfirmationDialog", Dialog), \
         patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget", pushed.append), \
         patch.object(compact.gui_app, "texture", lambda *_args: None):
      Path(self.params.get_param_path("Offset1")).write_bytes(b"bad")
      recovery = self.row("slc_reset")
      self.assertEqual(recovery.value, "Use default mph speed ranges")
      large._confirm_feature_reset(recovery)
      compact_adapter._confirm_reset(recovery, lambda: None)
      self.assertTrue(all("default mph speed ranges" in dialog.question for dialog in pushed[-2:]))

      self.assertTrue(self.owner.apply(self.confirm(recovery)))
      saved = self.row("slc_reset")
      self.assertEqual(saved.value, "Keep saved speed ranges")
      large._confirm_feature_reset(saved)
      compact_adapter._confirm_reset(saved, lambda: None)
      self.assertTrue(all("Keep saved speed ranges" in dialog.question for dialog in pushed[-2:]))
