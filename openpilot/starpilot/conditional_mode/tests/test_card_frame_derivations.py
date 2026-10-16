"""Frame-local pure derivations; live settings/authority checks still run."""
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from openpilot.common.params import Params
from openpilot.starpilot.conditional_mode import runtime_settings, status
from openpilot.starpilot.conditional_mode.card_settings import CardSettingsObservation, CardSettingsView, CardSettingsWorker
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.preferences import CCMOptions, CEMOptions, SavedPreferences
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, DocumentState, REVERIFY_NS, SafeModeState

NOW = 10_000_000_000


@pytest.fixture
def worker(tmp_path):
  result = CardSettingsWorker(Params(str(tmp_path)))
  result.refresh(NOW)
  result.adopt()
  return result


class UncachedCardSettingsView(CardSettingsView):
  # The live Card's 500ms source-age bound must remain in the reference too;
  # a generic owner has a different one-second bound. Only derivation is uncached.
  _selection_for_drive = ConditionalSettingsOwner._selection_for_drive


def reference(view):
  owner = UncachedCardSettingsView(view.owner_token)
  owner.current = view.current
  return owner


def outcome(owner, snapshot, now=NOW, drive=1):
  try:
    return owner.verdict(snapshot, now_mono_ns=now, drive_id=drive)
  except Exception as error:
    return type(error), str(error)


def test_reuses_only_pure_derivations_and_affirms_every_call(worker):
  view, snapshot = worker.view, worker.view.current
  expected = reference(view).verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  with patch.object(runtime_settings, 'saved_selection_for_drive', wraps=runtime_settings.saved_selection_for_drive) as selection, \
       patch.object(status, '_settings_fingerprint', wraps=status._settings_fingerprint) as fingerprint, \
       patch.object(view, 'affirm', wraps=view.affirm) as affirm, \
       patch.object(runtime_settings, 'read_mode_sources', side_effect=AssertionError('main-thread I/O')):
    for _ in range(4):
      assert view.refresh(NOW) is snapshot
      assert view.verdict(snapshot, now_mono_ns=NOW, drive_id=1) == expected
      assert status.settings_fingerprint(snapshot, owner=view) == status.settings_fingerprint(snapshot)
    assert selection.call_count == 1 and affirm.call_count == 4
    assert fingerprint.call_count == 5  # One cached miss plus four uncached references.


@pytest.mark.parametrize('now', [0, NOW - 1, NOW + REVERIFY_NS - 1, NOW + REVERIFY_NS, NOW + 1_000_000_001, True, 1.0])
def test_warm_cache_does_not_bypass_clock_and_stale_gates(worker, now):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  assert outcome(view, snapshot, now) == outcome(reference(view), snapshot, now)


@pytest.mark.parametrize('drive', [2, 0, -1, True, 1.0, '1', None])
def test_warm_cache_does_not_reuse_another_drive_or_accept_invalid_drive(worker, drive):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  assert outcome(view, snapshot, drive=drive) == outcome(reference(view), snapshot, drive=drive)


def test_adoption_clears_both_caches_even_for_the_same_snapshot(worker):
  view, snapshot = worker.view, worker.view.current
  with patch.object(runtime_settings, 'saved_selection_for_drive', wraps=runtime_settings.saved_selection_for_drive) as selection, \
       patch.object(status, '_settings_fingerprint', wraps=status._settings_fingerprint) as fingerprint:
    for _ in range(2):
      worker.adopt()
      view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
      status.settings_fingerprint(snapshot, owner=view)
    assert selection.call_count == fingerprint.call_count == 2


PREFERENCE_FIELDS = [('preferences', field.name) for field in fields(SavedPreferences)] + \
                    [('cem', field.name) for field in fields(CEMOptions)] + [('ccm', field.name) for field in fields(CCMOptions)]


@pytest.mark.parametrize('section,name', PREFERENCE_FIELDS)
def test_frozen_input_fixture_mutation_cannot_hide_behind_identity(worker, section, name):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  preferences = snapshot.preferences
  target = preferences if section == 'preferences' else getattr(preferences, section)
  previous = getattr(target, name)
  if type(previous) is bool:
    changed = not previous
  elif type(previous) in (int, float):
    changed = previous + 0.125
  elif type(previous) is ModeChoice:
    changed = ModeChoice.CCM if previous is not ModeChoice.CCM else ModeChoice.CEM
  elif type(previous) is CEMOptions:
    changed = replace(previous, curves=not previous.curves)
  elif type(previous) is CCMOptions:
    changed = replace(previous, lead=not previous.lead)
  else:
    raise AssertionError(type(previous))
  try:
    object.__setattr__(target, name, changed)
    assert outcome(view, snapshot) == outcome(reference(view), snapshot)
  finally:
    object.__setattr__(target, name, previous)


@pytest.mark.parametrize('preferences', [SimpleNamespace(), replace(SavedPreferences(), cem=SimpleNamespace()),
                                         replace(SavedPreferences(), ccm=SimpleNamespace()),
                                         replace(SavedPreferences(), version='invalid')])
def test_custom_or_malformed_preferences_follow_original_failure(worker, preferences):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  changed = replace(snapshot, preferences=preferences)
  view.adopt(CardSettingsObservation(changed, 'verified', NOW))
  assert outcome(view, changed) == outcome(reference(view), changed)


@pytest.mark.parametrize('field,value', [('document_raw', b'{}'), ('safe_mode_raw', b'0'),
                                        ('document_state', DocumentState.INVALID), ('safe_mode_state', SafeModeState.TRUE),
                                        ('safe_mode_raw', bytearray(b'0'))])
def test_fingerprint_reads_current_values_and_preserves_fallback(worker, field, value):
  view, snapshot = worker.view, worker.view.current
  status.settings_fingerprint(snapshot, owner=view)
  previous = getattr(snapshot, field)
  try:
    object.__setattr__(snapshot, field, value)
    assert status.settings_fingerprint(snapshot, owner=view) == status.settings_fingerprint(snapshot)
  finally:
    object.__setattr__(snapshot, field, previous)


def test_foreign_snapshots_and_custom_view_subclasses_do_not_use_cache(worker):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  foreign = replace(snapshot, owner_token='foreign')
  assert outcome(view, foreign) == outcome(reference(view), foreign)

  class CustomView(CardSettingsView):
    pass

  custom = CustomView(view.owner_token)
  custom.adopt(worker.published)
  generic = reference(custom)
  with patch.object(runtime_settings, 'saved_selection_for_drive', wraps=runtime_settings.saved_selection_for_drive) as selection:
    for _ in range(2):
      assert custom.verdict(snapshot, now_mono_ns=NOW, drive_id=1) == generic.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
    assert selection.call_count == 4
  assert custom._selection_cache is None and custom._fingerprint_cache is None
  assert status.settings_fingerprint(snapshot, owner=object()) == status.settings_fingerprint(snapshot)


def test_deleted_nested_fixture_field_preserves_original_error_order(worker):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  preferences = snapshot.preferences
  previous = preferences.cem
  try:
    object.__setattr__(preferences, 'version', 'invalid')
    object.__delattr__(preferences, 'cem')
    assert outcome(view, snapshot) == outcome(reference(view), snapshot)
  finally:
    object.__setattr__(preferences, 'version', 1)
    object.__setattr__(preferences, 'cem', previous)


@pytest.mark.parametrize('field,value', [('safe_mode_state', SafeModeState.TRUE),
                                        ('safe_mode_state', SafeModeState.INVALID),
                                        ('document_state', DocumentState.READ_ERROR),
                                        ('owner_token', 'foreign')])
def test_current_source_gate_changes_after_warm_cache_still_deny(worker, field, value):
  view, snapshot = worker.view, worker.view.current
  view.verdict(snapshot, now_mono_ns=NOW, drive_id=1)
  changed = replace(snapshot, **{field: value})
  # Deliberately replace the live source without adopt to verify the cache is
  # subordinate to current owner/source gates, not just adoption bookkeeping.
  view.current = changed
  assert outcome(view, changed) == outcome(reference(view), changed)
  assert outcome(view, snapshot) == outcome(reference(view), snapshot)


@pytest.mark.parametrize('full_op', [False, True])
def test_actual_card_adoption_and_multiple_consumers_keep_live_authority(full_op):
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car import card as module
  from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests
  from openpilot.starpilot.conditional_mode.manual import ButtonTracker, IoniqMediaMapCache

  fixture = IoniqAvailabilityTests()
  try:
    with OpenpilotPrefix():
      sd, _, drive, card, receive = fixture._ioniq_availability_callers(full_op=full_op)
      card.conditional_replay = True
      card.manual_button_tracker = ButtonTracker()
      card.traffic_button_tracker = ButtonTracker()
      card.ioniq_media_map = IoniqMediaMapCache()
      card.manual_settings_owner = ConditionalSettingsOwner(card.params)
      with patch.object(module, 'REPLAY', False):
        card.configure_conditional_settings_worker()
      worker = card.conditional_settings_worker
      for tick in (2, 3):
        now = NOW + tick * 10_000_000
        worker.refresh(now)
        axis, _, command = drive(tick)
        with patch.object(runtime_settings, 'saved_selection_for_drive', wraps=runtime_settings.saved_selection_for_drive) as selection, \
             patch.object(worker.view, 'affirm', wraps=worker.view.affirm) as affirm:
          assert receive(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
        assert selection.call_count == 1
        assert affirm.call_count >= (2 if full_op else 1)
        assert axis.lateralActive and command.latActive
        assert bool(axis.longitudinalActive) is full_op and bool(command.longActive) is full_op
      # A fresh restrictive worker publication must revoke optional proposals.
      Path(card.params.get_param_path('ConditionalModeConfig')).write_bytes(b'{')
      now = NOW + 40_000_000
      worker.refresh(now)
      axis, _, command = drive(4)
      assert receive(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert worker.view.verdict(worker.view.current, now_mono_ns=now, drive_id=NOW - 1_000_000_000).status == 'unavailable_document'
      assert card.manual_receipt is None and card.traffic_receipt is None and card.switchback_receipt is None
      assert axis.lateralActive and command.latActive
      assert bool(axis.longitudinalActive) is full_op and bool(command.longActive) is full_op
  finally:
    fixture.doCleanups()
