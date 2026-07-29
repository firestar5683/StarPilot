import time
from types import SimpleNamespace

from cereal import car, custom, log

from opendbc.car import CanData
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.interface import EV9PandaPreinitFlags, EV9PandaPreinitHandoff, EV9PandaPreinitOwner, EV9PandaPreinitState, \
                                            attempt_ev9_pre_fingerprint_suppression, \
                                            update_ev9_panda_preinit_handoff
from openpilot.selfdrive.car.ev9_preinit import EV9_PREINIT_MANAGED_FRAMES, EV9PreinitFaultHistory, EV9PreinitOffSample, \
                                                EV9PreinitTakeoverState, \
                                                collect_ev9_preinit_baselines, \
                                                collect_ev9_preinit_claim_receipts, complete_ev9_preinit_baselines, \
                                                collect_ev9_preinit_rejected_outputs, \
                                                complete_ev9_preinit_claim_receipts, ev9_preinit_allows_fw_query, \
                                                ev9_preinit_classify_off_sample, \
                                                ev9_preinit_expected_off_transition, \
                                                ev9_preinit_expected_safety_rejection, \
                                                ev9_preinit_health_snapshot, ev9_preinit_health_unchanged, \
                                                ev9_preinit_off_reclaim_failed, \
                                                ev9_preinit_off_reclaim_ready, \
                                                ev9_preinit_panda_fault_acceptable, ev9_preinit_panda_fault_recovered, \
                                                ev9_preinit_refreshed_takeover_allowed, \
                                                ensure_ev9_preinit_claim_retries, \
                                                ev9_preinit_parser_packets, ev9_preinit_recovered_fault_dwell_complete, \
                                                ev9_preinit_safety_ready, load_cached_car_params, \
                                                load_cached_starpilot_car_params, normalize_ev9_cached_starpilot_safety, \
                                                revalidate_ev9_panda_preinit_handoff, \
                                                ev9_preinit_resident_ignition_on, \
                                                ev9_preinit_terminal_ignition_on, \
                                                ev9_preinit_warm_start_pending


class FakeParams:
  def __init__(self, values=None):
    self.values = values or {}

  def get(self, key):
    return self.values.get(key)

  def get_bool(self, key):
    return bool(self.values.get(key, False))


def _panda_preinit_status(state: EV9PandaPreinitState, ignition: bool, flags: int = 0,
                          cycle_started_us: int = 0, timing_valid: bool = True):
  status = SimpleNamespace(
    resident=True,
    valid=True,
    version=4,
    state=int(state),
    flags=flags,
    communicationType=1,
    timingValid=timing_valid,
    cycleStartedUs=cycle_started_us,
  )
  panda_state = SimpleNamespace(
    ev9LongPreinitStatus=status,
    ignitionLine=ignition,
    ignitionCan=False,
  )
  return panda_state, update_ev9_panda_preinit_handoff([panda_state])


def test_expected_off_transition_accepts_one_coherent_low_or_torn_high_terminal_sample():
  for resident_state in (EV9PandaPreinitState.RESTORING, EV9PandaPreinitState.ABORTED):
    for ignition, expected_sample in ((False, EV9PreinitOffSample.SAME_TERMINAL_LOW),
                                      (True, EV9PreinitOffSample.SAME_TERMINAL_HIGH)):
      panda_state, handoff = _panda_preinit_status(resident_state, ignition=ignition, cycle_started_us=100)
      off_sample = ev9_preinit_classify_off_sample(handoff, [panda_state], 100)
      terminal_ignition_on = ev9_preinit_terminal_ignition_on(handoff, [panda_state])
      assert off_sample == expected_sample
      for takeover_state in (EV9PreinitTakeoverState.CLAIMING, EV9PreinitTakeoverState.CONFIRMED):
        assert ev9_preinit_expected_off_transition(takeover_state, off_sample, terminal_ignition_on)

      assert not ev9_preinit_expected_off_transition(EV9PreinitTakeoverState.WAIT_SAFETY, off_sample, terminal_ignition_on)

  panda_state, handoff = _panda_preinit_status(EV9PandaPreinitState.ACTIVE, ignition=False, cycle_started_us=100)
  off_sample = ev9_preinit_classify_off_sample(handoff, [panda_state], 100)
  assert off_sample == EV9PreinitOffSample.NONE
  assert not ev9_preinit_expected_off_transition(EV9PreinitTakeoverState.CONFIRMED, off_sample, None)

  handoff_panda, handoff = _panda_preinit_status(
    EV9PandaPreinitState.HANDOFF, ignition=False, cycle_started_us=100,
  )
  assert ev9_preinit_resident_ignition_on(handoff, [handoff_panda]) is False
  assert ev9_preinit_expected_off_transition(
    EV9PreinitTakeoverState.CONFIRMED, EV9PreinitOffSample.NONE, None, False,
  )

  torn_panda, torn_handoff = _panda_preinit_status(
    EV9PandaPreinitState.RESTORING, ignition=True, cycle_started_us=100, timing_valid=False,
  )
  torn_sample = ev9_preinit_classify_off_sample(torn_handoff, [torn_panda], 100)
  torn_ignition = ev9_preinit_terminal_ignition_on(torn_handoff, [torn_panda])
  assert torn_sample == EV9PreinitOffSample.NONE
  assert torn_ignition is True
  assert ev9_preinit_expected_off_transition(EV9PreinitTakeoverState.CONFIRMED, torn_sample, torn_ignition)


def test_warm_start_pending_is_scoped_to_armed_ignition_high_aborted():
  panda_state, handoff = _panda_preinit_status(EV9PandaPreinitState.ABORTED, ignition=True)
  assert ev9_preinit_warm_start_pending(True, handoff, [panda_state])
  assert not ev9_preinit_warm_start_pending(False, handoff, [panda_state])

  panda_state.ignitionLine = False
  assert not ev9_preinit_warm_start_pending(True, handoff, [panda_state])

  restoring_panda, restoring_handoff = _panda_preinit_status(EV9PandaPreinitState.RESTORING, ignition=True)
  assert not ev9_preinit_warm_start_pending(True, restoring_handoff, [restoring_panda])


def test_refreshed_active_handoff_supersedes_initial_pending_startup_decision():
  _, pending_handoff = _panda_preinit_status(
    EV9PandaPreinitState.WAIT_SESSION, ignition=True, cycle_started_us=200,
  )
  active_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                     EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                     EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  _, active_handoff = _panda_preinit_status(
    EV9PandaPreinitState.ACTIVE, ignition=True, flags=active_flags, cycle_started_us=200,
  )

  assert not ev9_preinit_refreshed_takeover_allowed(True, pending_handoff, True)
  assert ev9_preinit_refreshed_takeover_allowed(True, active_handoff, True)
  assert not ev9_preinit_refreshed_takeover_allowed(False, active_handoff, True)
  assert not ev9_preinit_refreshed_takeover_allowed(True, active_handoff, False)
  assert not ev9_preinit_refreshed_takeover_allowed(False, EV9PandaPreinitHandoff(), True)


def test_off_reclaim_requires_fresh_coherent_active_panda_epoch():
  active_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                     EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                     EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  panda_state, handoff = _panda_preinit_status(
    EV9PandaPreinitState.ACTIVE, ignition=True, flags=active_flags, cycle_started_us=200,
  )
  assert ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, handoff, [panda_state], 100)
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, handoff, [panda_state], 200)
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.CONFIRMED, handoff, [panda_state], 100)

  panda_state.ignitionLine = False
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, handoff, [panda_state], 100)

  pending_panda, pending_handoff = _panda_preinit_status(
    EV9PandaPreinitState.WAIT_SESSION, ignition=True, cycle_started_us=200,
  )
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, pending_handoff, [pending_panda], 100)

  failed_panda, failed_handoff = _panda_preinit_status(
    EV9PandaPreinitState.ABORTED, ignition=True, cycle_started_us=200,
  )
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, failed_handoff, [failed_panda], 100)
  assert ev9_preinit_off_reclaim_failed(EV9PreinitTakeoverState.OFF, failed_handoff, [failed_panda], 100)

  incoherent_panda, incoherent_handoff = _panda_preinit_status(
    EV9PandaPreinitState.ACTIVE, ignition=True, flags=active_flags, cycle_started_us=200, timing_valid=False,
  )
  assert not ev9_preinit_off_reclaim_ready(EV9PreinitTakeoverState.OFF, incoherent_handoff, [incoherent_panda], 100)


def test_runtime_fast_warm_pending_then_active_reseals_before_normal_takeover():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  active_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                     EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                     EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  pending_panda, _ = _panda_preinit_status(
    EV9PandaPreinitState.WAIT_SESSION, ignition=True, cycle_started_us=200,
  )
  old_fault_history = EV9PreinitFaultHistory()
  old_fault_history.initialized = True
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_fault_history = old_fault_history
  card_instance.ev9_preinit_health_baseline = (1, 2, 3)
  card_instance.ev9_preinit_claim_receipts = {(1, 0x730)}
  card_instance.ev9_preinit_claim_last_host_tx_us = 99
  card_instance.ev9_preinit_claim_started = 12.0
  card_instance.ev9_preinit_last_status_time = 10.0
  card_instance.ev9_preinit_off_high_pending = True
  card_instance.ev9_preinit_off_high_pending_started = 9.5
  card_instance.ev9_preinit_resume_fresh_can = False
  card_instance.sm = FakeSubMaster([pending_panda])
  prepared = []

  def prepare_takeover():
    prepared.append(True)
    assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
    assert card_instance.ev9_preinit_fault_history is not old_fault_history
    assert not card_instance.ev9_preinit_fault_history.initialized
    assert card_instance.ev9_preinit_health_baseline is None
    assert card_instance.ev9_preinit_claim_receipts == set()
    assert card_instance.ev9_preinit_claim_last_host_tx_us == 0
    assert card_instance.ev9_preinit_claim_started == 0.0
    assert card_instance.ev9_preinit_last_status_time == 0.0
    card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED

  card_instance._prepare_ev9_panda_takeover = prepare_takeover

  card_instance._update_ev9_panda_takeover()
  assert prepared == []
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
  assert not card_instance.ev9_preinit_off_high_pending
  assert card_instance.ev9_preinit_off_high_pending_started == 0.0

  active_panda, _ = _panda_preinit_status(
    EV9PandaPreinitState.ACTIVE, ignition=True, flags=active_flags, cycle_started_us=200,
  )
  card_instance.sm.panda_states = [active_panda]
  card_instance._update_ev9_panda_takeover()

  assert prepared == [True]
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.CONFIRMED
  assert card_instance.ev9_preinit_resume_fresh_can


def test_runtime_off_reclaim_rejects_same_cycle_low_ignition_and_pending():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  active_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                     EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                     EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  cases = (
    (EV9PandaPreinitState.ACTIVE, True, active_flags, 100),
    (EV9PandaPreinitState.ACTIVE, False, active_flags, 200),
    (EV9PandaPreinitState.WAIT_SESSION, True, 0, 200),
  )
  for resident_state, ignition, flags, cycle_started_us in cases:
    panda_state, _ = _panda_preinit_status(
      resident_state, ignition=ignition, flags=flags, cycle_started_us=cycle_started_us,
    )
    card_instance = Car.__new__(Car)
    card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
    card_instance.ev9_preinit_cycle_started_us = 100
    card_instance.ev9_preinit_off_high_pending = False
    card_instance.ev9_preinit_off_high_pending_started = 0.0
    card_instance.sm = FakeSubMaster([panda_state])
    prepared = []
    card_instance._prepare_ev9_panda_takeover = lambda prepared=prepared: prepared.append(True)

    card_instance._update_ev9_panda_takeover()

    assert prepared == []
    assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF


def test_runtime_off_fresh_failed_epoch_faults_closed():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  class RecordingParams:
    def __init__(self):
      self.values = {}

    def put_bool(self, key, value):
      self.values[key] = value

  panda_state, _ = _panda_preinit_status(
    EV9PandaPreinitState.ABORTED, ignition=True, cycle_started_us=200,
  )
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.params = RecordingParams()
  card_instance.CI = SimpleNamespace(CC=SimpleNamespace(ecu_disable_failed=False, long_active_ecu=True))
  card_instance.sm = FakeSubMaster([panda_state])

  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.FAULTED
  assert card_instance.params.values == {"EcuDisableFailed": True}


def test_runtime_confirmed_off_wait_does_not_inherit_active_epoch_status_timeout():
  from openpilot.selfdrive.car.card import Car

  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_off_high_pending = False
  card_instance.ev9_preinit_off_high_pending_started = 0.0
  card_instance.sm = SimpleNamespace(updated={"pandaStates": False})
  card_instance._fault_ev9_panda_takeover = lambda _reason: (_ for _ in ()).throw(
    AssertionError("OFF must wait without the completed epoch's runtime status timeout"),
  )

  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF


def test_runtime_torn_high_pending_without_new_publication_times_out():
  from openpilot.selfdrive.car.card import Car

  class RecordingParams:
    def __init__(self):
      self.values = {}

    def put_bool(self, key, value):
      self.values[key] = value

  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_off_high_pending = True
  card_instance.ev9_preinit_off_high_pending_started = time.monotonic() - 0.6
  card_instance.params = RecordingParams()
  card_instance.CI = SimpleNamespace(CC=SimpleNamespace(ecu_disable_failed=False, long_active_ecu=True))
  card_instance.sm = SimpleNamespace(updated={"pandaStates": False})

  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.FAULTED
  assert card_instance.params.values == {"EcuDisableFailed": True}


def test_runtime_repeated_incoherent_high_publications_cannot_refresh_pending_timeout():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  class RecordingParams:
    def __init__(self):
      self.values = {}

    def put_bool(self, key, value):
      self.values[key] = value

  torn_high, _ = _panda_preinit_status(
    EV9PandaPreinitState.RESTORING, ignition=True, cycle_started_us=100, timing_valid=False,
  )
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.OFF
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_off_high_pending = True
  card_instance.ev9_preinit_off_high_pending_started = time.monotonic() - 0.6
  card_instance.params = RecordingParams()
  card_instance.CI = SimpleNamespace(CC=SimpleNamespace(ecu_disable_failed=False, long_active_ecu=True))
  card_instance.sm = FakeSubMaster([torn_high])

  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.FAULTED
  assert card_instance.params.values == {"EcuDisableFailed": True}


def test_runtime_first_low_or_torn_high_terminal_sample_enters_off_before_health_gate():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  class UnusedFaultHistory:
    @staticmethod
    def update(_panda_states):
      raise AssertionError("expected OFF must precede fault and health gates")

  handoff_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                      EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                      EV9PandaPreinitFlags.BRIDGE_ACTIVE |
                      EV9PandaPreinitFlags.HOST_HANDOFF)
  for resident_state, ignition, flags in ((EV9PandaPreinitState.RESTORING, False, 0),
                                          (EV9PandaPreinitState.RESTORING, True, 0),
                                          (EV9PandaPreinitState.ABORTED, False, 0),
                                          (EV9PandaPreinitState.ABORTED, True, 0),
                                          (EV9PandaPreinitState.HANDOFF, False, handoff_flags)):
    panda_state, _ = _panda_preinit_status(
      resident_state, ignition=ignition, flags=flags, cycle_started_us=100,
    )
    card_instance = Car.__new__(Car)
    card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
    card_instance.ev9_preinit_cycle_started_us = 100
    card_instance.ev9_preinit_claim_receipts = {(1, 0x730)}
    card_instance.ev9_preinit_claim_started = 12.0
    card_instance.ev9_preinit_last_status_time = 0.0
    card_instance.ev9_preinit_fault_history = UnusedFaultHistory()
    card_instance.sm = FakeSubMaster([panda_state])

    card_instance._update_ev9_panda_takeover()

    assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
    assert card_instance.ev9_preinit_claim_receipts == set()
    assert card_instance.ev9_preinit_claim_started == 0.0
    assert card_instance.ev9_preinit_last_status_time > 0.0
    assert card_instance.ev9_preinit_off_high_pending == ignition
    assert (card_instance.ev9_preinit_off_high_pending_started > 0.0) == ignition


def test_runtime_torn_high_terminal_then_coherent_low_confirms_off():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  torn_high, _ = _panda_preinit_status(
    EV9PandaPreinitState.RESTORING, ignition=True, cycle_started_us=100, timing_valid=False,
  )
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_claim_receipts = {(1, 0x730)}
  card_instance.ev9_preinit_claim_started = 12.0
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_fault_history = SimpleNamespace(
    update=lambda _panda_states: (_ for _ in ()).throw(AssertionError("torn OFF must precede health gates")),
  )
  card_instance.sm = FakeSubMaster([torn_high])

  card_instance._update_ev9_panda_takeover()
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
  assert card_instance.ev9_preinit_off_high_pending

  coherent_low, _ = _panda_preinit_status(
    EV9PandaPreinitState.ABORTED, ignition=False, cycle_started_us=100,
  )
  card_instance.sm.panda_states = [coherent_low]
  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
  assert not card_instance.ev9_preinit_off_high_pending
  assert card_instance.ev9_preinit_off_high_pending_started == 0.0


def test_runtime_torn_high_terminal_then_second_coherent_high_faults():
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  class RecordingParams:
    def __init__(self):
      self.values = {}

    def put_bool(self, key, value):
      self.values[key] = value

  torn_high, _ = _panda_preinit_status(
    EV9PandaPreinitState.RESTORING, ignition=True, cycle_started_us=100, timing_valid=False,
  )
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_claim_receipts = set()
  card_instance.ev9_preinit_claim_started = 0.0
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_fault_history = SimpleNamespace(update=lambda _panda_states: True)
  card_instance.params = RecordingParams()
  card_instance.CI = SimpleNamespace(CC=SimpleNamespace(ecu_disable_failed=False, long_active_ecu=True))
  card_instance.sm = FakeSubMaster([torn_high])

  card_instance._update_ev9_panda_takeover()
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.OFF
  assert card_instance.ev9_preinit_off_high_pending

  coherent_high, _ = _panda_preinit_status(
    EV9PandaPreinitState.ABORTED, ignition=True, cycle_started_us=100,
  )
  card_instance.sm.panda_states = [coherent_high]
  card_instance._update_ev9_panda_takeover()

  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.FAULTED
  assert card_instance.params.values == {"EcuDisableFailed": True}


def test_confirmed_handoff_does_not_add_runtime_transaction_faults(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  class RecordingParams:
    def __init__(self):
      self.values = {}

    def put_bool(self, key, value):
      self.values[key] = value

  handoff_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                      EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                      EV9PandaPreinitFlags.BRIDGE_ACTIVE |
                      EV9PandaPreinitFlags.HOST_HANDOFF)
  for safety_ready, health_unchanged in ((False, True), (True, False)):
    panda_state, _ = _panda_preinit_status(
      EV9PandaPreinitState.HANDOFF, ignition=True, flags=handoff_flags, cycle_started_us=100,
    )
    monkeypatch.setattr(card_module, "ev9_preinit_safety_ready", lambda *_args, ready=safety_ready: ready)
    monkeypatch.setattr(card_module, "ev9_preinit_health_unchanged", lambda *_args, unchanged=health_unchanged: unchanged)

    card_instance = Car.__new__(Car)
    card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
    card_instance.ev9_preinit_cycle_started_us = 100
    card_instance.ev9_preinit_claim_receipts = set()
    card_instance.ev9_preinit_claim_started = 0.0
    card_instance.ev9_preinit_last_status_time = 0.0
    card_instance.ev9_preinit_health_baseline = ()
    card_instance.ev9_preinit_fault_history = SimpleNamespace(update=lambda _panda_states: True)
    card_instance._expected_ev9_panda_safety = lambda: ("hyundaiCanfd", 0xA5, 0)
    card_instance.params = RecordingParams()
    card_instance.CI = SimpleNamespace(CC=SimpleNamespace(ecu_disable_failed=False, long_active_ecu=True))
    card_instance.sm = FakeSubMaster([panda_state])

    card_instance._update_ev9_panda_takeover()

    assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.CONFIRMED
    assert card_instance.params.values == {}


def test_confirmed_handoff_leaves_safety_rejections_to_normal_panda_handling(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}
    seen = {"carControl": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states
      self.car_control = SimpleNamespace(enabled=False, latActive=True)

    def __getitem__(self, service):
      if service == "pandaStates":
        return self.panda_states
      if service == "carControl":
        return self.car_control
      raise KeyError(service)

  flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
              EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
              EV9PandaPreinitFlags.BRIDGE_ACTIVE |
              EV9PandaPreinitFlags.HOST_HANDOFF)
  panda_state, _ = _panda_preinit_status(
    EV9PandaPreinitState.HANDOFF, ignition=True, flags=flags, cycle_started_us=100,
  )
  can_state = SimpleNamespace(
    canCoreResetCnt=0, busOffCnt=0, totalErrorCnt=0, totalTxLostCnt=0, totalRxLostCnt=0,
  )
  panda_state.rxBufferOverflow = 0
  panda_state.txBufferOverflow = 0
  panda_state.safetyTxBlocked = 0
  panda_state.canState0 = can_state
  panda_state.canState1 = can_state
  panda_state.canState2 = can_state
  baseline = ev9_preinit_health_snapshot([panda_state])
  panda_state.safetyTxBlocked = 1
  monkeypatch.setattr(card_module, "ev9_preinit_safety_ready", lambda *_args: True)

  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_claim_receipts = set()
  card_instance.ev9_preinit_claim_started = 0.0
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_health_baseline = baseline
  card_instance.ev9_preinit_health_pending = None
  card_instance.ev9_preinit_safety_quarantine = False
  # Route 1a4 published safetyTxBlocked=1 after both exact rejected active
  # 0xCB receipts were already queued. This is normal 10 Hz status/receipt
  # skew during live VM angle enforcement, not a CAN transport fault.
  route_1a4_cb = bytes.fromhex("37ee8020c43fc60000000000000000000000000000000000")
  card_instance.ev9_preinit_rejected_outputs = [
    (1.0, CanData(0xCB, route_1a4_cb, 0xC1)),
    (1.01, CanData(0xCB, route_1a4_cb, 0xC1)),
  ]
  card_instance.ev9_preinit_fault_history = SimpleNamespace(update=lambda _panda_states: True)
  card_instance._expected_ev9_panda_safety = lambda: ("hyundaiCanfdEv9", 0xC95, 32)
  card_instance.CI = SimpleNamespace(CS=SimpleNamespace(
    out=SimpleNamespace(gearShifter=car.CarState.GearShifter.drive),
  ))
  card_instance.sm = FakeSubMaster([panda_state])

  card_instance._update_ev9_panda_takeover()
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.CONFIRMED
  assert card_instance.ev9_preinit_health_baseline == baseline
  assert card_instance.ev9_preinit_health_pending is None
  assert not card_instance.ev9_preinit_safety_quarantine

  # Cumulative safety counters remain ordinary Panda telemetry after handoff;
  # the preinit transaction no longer creates a second fault/quarantine layer.
  panda_state.safetyTxBlocked = 2
  card_instance._update_ev9_panda_takeover()
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.CONFIRMED
  assert card_instance.ev9_preinit_health_baseline == baseline
  assert card_instance.ev9_preinit_health_pending is None
  assert not card_instance.ev9_preinit_safety_quarantine


def test_confirmed_handoff_does_not_reclaim_on_runtime_lease_sample(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    updated = {"pandaStates": True}

    def __init__(self, panda_states):
      self.panda_states = panda_states

    def __getitem__(self, service):
      assert service == "pandaStates"
      return self.panda_states

  active_flags = int(EV9PandaPreinitFlags.IDENTITY_VALID |
                     EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
                     EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  panda_state, _ = _panda_preinit_status(
    EV9PandaPreinitState.ACTIVE, ignition=True, flags=active_flags, cycle_started_us=100,
  )
  panda_state.ev9LongPreinitStatus.lastHostTxUs = 77
  monkeypatch.setattr(card_module, "ev9_preinit_safety_ready", lambda *_args: True)
  monkeypatch.setattr(card_module, "ev9_preinit_health_unchanged", lambda *_args: True)

  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  card_instance.ev9_preinit_cycle_started_us = 100
  card_instance.ev9_preinit_last_status_time = 0.0
  card_instance.ev9_preinit_health_baseline = ()
  card_instance.ev9_preinit_claim_last_host_tx_us = 0
  card_instance.ev9_preinit_resume_fresh_can = False
  card_instance.ev9_preinit_fault_history = SimpleNamespace(update=lambda _panda_states: True)
  card_instance._expected_ev9_panda_safety = lambda: ("hyundaiCanfd", 0xA5, 0)
  card_instance.sm = FakeSubMaster([panda_state])
  claim_calls = []

  def run_claim(timeout_s, resume_fresh_can=False):
    claim_calls.append((timeout_s, resume_fresh_can, card_instance.ev9_preinit_claim_last_host_tx_us))
    card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
    card_instance.ev9_preinit_resume_fresh_can = resume_fresh_can
    return True

  card_instance._run_ev9_panda_claim = run_claim
  card_instance._update_ev9_panda_takeover()

  assert claim_calls == []
  assert card_instance.ev9_preinit_takeover_state == EV9PreinitTakeoverState.CONFIRMED
  assert not card_instance.ev9_preinit_resume_fresh_can


def test_step_sends_nothing_before_fresh_claim(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    seen = {"onroadEvents": True}

    def __getitem__(self, service):
      if service == "onroadEvents":
        return []
      if service == "carControl":
        return SimpleNamespace()
      raise KeyError(service)

  monkeypatch.setattr(card_module, "get_starpilot_toggles", lambda *_args: SimpleNamespace())

  for takeover_state in (EV9PreinitTakeoverState.OFF, EV9PreinitTakeoverState.WAIT_SAFETY,
                         EV9PreinitTakeoverState.FAULTED):
    sent = []
    card_instance = Car.__new__(Car)
    card_instance.ev9_preinit_takeover_state = takeover_state
    card_instance.ev9_preinit_resume_fresh_can = False
    card_instance.ev9_early_control_active = True
    card_instance.CP = SimpleNamespace(passive=False)
    card_instance.CI = SimpleNamespace(CS=SimpleNamespace())
    card_instance.sm = FakeSubMaster()
    card_instance.state_update = lambda: (SimpleNamespace(canValid=True), None, SimpleNamespace())
    card_instance.state_publish = lambda *_args: None
    card_instance.controls_update = lambda *_args, sent=sent: sent.append("controls")
    card_instance._send_ev9_early_inactive_reconstruction = lambda *_args, sent=sent: sent.append("early")

    card_instance.step()

    assert sent == []


def test_ev9_actuation_interlock_rejects_current_and_latched_panda_faults():
  from openpilot.selfdrive.car.card import ev9_panda_faulted_for_actuation

  healthy = SimpleNamespace(faults=[], faultStatus=0)
  current_fault = SimpleNamespace(faults=[1], faultStatus=0)
  latched_fault = SimpleNamespace(faults=[], faultStatus=1)
  permanent_fault = SimpleNamespace(faults=[], faultStatus=2)

  assert ev9_panda_faulted_for_actuation([], False)
  assert not ev9_panda_faulted_for_actuation([healthy], True)
  assert ev9_panda_faulted_for_actuation([current_fault], True)
  assert not ev9_panda_faulted_for_actuation([latched_fault], True)
  assert ev9_panda_faulted_for_actuation([permanent_fault], True)


def test_ev9_actuation_interlock_accepts_real_capnp_fault_status_enum():
  from openpilot.selfdrive.car.card import ev9_panda_faulted_for_actuation

  panda_state = log.PandaState.new_message()
  assert str(panda_state.faultStatus) == "none"
  assert not ev9_panda_faulted_for_actuation([panda_state], True)

  panda_state.faultStatus = "faultTemp"
  assert not ev9_panda_faulted_for_actuation([panda_state], True)

  panda_state.faults = ["interruptRateCan3"]
  assert ev9_panda_faulted_for_actuation([panda_state], True)


def test_ev9_actuation_interlock_rejects_even_authorized_recovered_can3_fault():
  from openpilot.selfdrive.car.card import ev9_panda_faulted_for_actuation

  recovered = SimpleNamespace(
    faults=["interruptRateCan3"], faultStatus="faultTemp",
    ev9LongPreinitStatus=SimpleNamespace(resident=True),
  )

  assert ev9_panda_faulted_for_actuation([], True)
  assert ev9_panda_faulted_for_actuation([recovered], True)


def test_claim_scheduler_uses_bounded_three_ms_retry_and_one_ms_status_poll():
  from openpilot.selfdrive.car import card as card_module

  assert card_module.EV9_PANDA_PREINIT_CLAIM_RETRY_S == 0.003
  assert card_module.EV9_PANDA_PREINIT_CLAIM_POLL_MS == 1
  # A 3 ms phase walk reaches the final 10% admission window for every
  # managed cadence; a 10 ms walk does not for the 10/20/50 ms classes.
  for period_ms in (10, 20, 50, 200):
    phases = {(step * 3) % period_ms for step in range(period_ms)}
    assert any(phase >= period_ms * 0.9 for phase in phases)


def test_shared_claim_primes_controller_once_then_uses_frozen_three_ms_retries(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeTime:
    now = 0.0

    def monotonic(self):
      return self.now

    def sleep(self, seconds):
      self.now += seconds

  class FakeSubMaster:
    updated = {"pandaStates": False}

    def __init__(self, fake_time):
      self.fake_time = fake_time
      self.polls = []

    def update(self, timeout_ms):
      self.polls.append(timeout_ms)
      self.fake_time.now += timeout_ms / 1000.0

  fake_time = FakeTime()
  monkeypatch.setattr(card_module, "time", fake_time)
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_claim_receipts = set()
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  # The firmware knockout is stationary-gated, but adoption is deliberately
  # stock-like: a cold comma may claim the already-suppressed ECU after the
  # driver has pulled away.
  card_instance.CI = SimpleNamespace(CS=SimpleNamespace(out=SimpleNamespace(
    vEgo=15.0, standstill=False, gearShifter=car.CarState.GearShifter.drive,
  )))
  card_instance._expected_ev9_panda_safety = lambda: ("hyundaiCanfd", 0xA5, 0)
  card_instance._drain_ev9_preinit_can = lambda **_kwargs: None
  card_instance.sm = FakeSubMaster(fake_time)
  primed_at = []
  retried_at = []
  card_instance._send_ev9_early_inactive_reconstruction = \
    lambda valid: primed_at.append((valid, fake_time.now)) or True
  card_instance._send_ev9_panda_claim_retries = lambda: retried_at.append(fake_time.now) or False

  assert not card_instance._run_ev9_panda_claim(1.0)

  assert primed_at == [(True, 0.0)]
  assert len(retried_at) == 1
  assert round(retried_at[0] * 1000) == 3
  assert card_instance.sm.polls == [1, 1]


def test_step_consumes_runtime_reclaim_barrier_before_resuming_controls(monkeypatch):
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car

  class FakeSubMaster:
    seen = {"onroadEvents": True}

    def __getitem__(self, service):
      if service == "onroadEvents":
        return []
      if service == "carControl":
        return SimpleNamespace()
      raise KeyError(service)

  sent = []
  state_updates = []
  card_instance = Car.__new__(Car)
  card_instance.ev9_preinit_takeover_state = EV9PreinitTakeoverState.CONFIRMED
  card_instance.ev9_preinit_resume_fresh_can = True
  card_instance.ev9_early_control_active = True
  card_instance.CP = SimpleNamespace(passive=False)
  card_instance.CI = SimpleNamespace(CS=SimpleNamespace())
  card_instance.sm = FakeSubMaster()

  def state_update():
    state_updates.append(True)
    return SimpleNamespace(canValid=True), None, SimpleNamespace()

  card_instance.state_update = state_update
  card_instance.state_publish = lambda *_args: None
  card_instance.controls_update = lambda *_args: sent.append("controls")
  card_instance._send_ev9_early_inactive_reconstruction = lambda *_args: sent.append("early")
  monkeypatch.setattr(card_module, "get_starpilot_toggles", lambda *_args: SimpleNamespace())

  card_instance.step()
  assert state_updates == [True]
  assert sent == []
  assert not card_instance.ev9_preinit_resume_fresh_can

  card_instance.step()
  assert state_updates == [True, True]
  assert sent == ["controls"]


def test_cached_params_tolerate_missing_and_corrupt_values():
  assert load_cached_car_params(FakeParams()) is None
  assert load_cached_starpilot_car_params(FakeParams()) is None
  assert load_cached_car_params(FakeParams({"CarParamsCache": b"not-capnp"})) is None
  assert load_cached_starpilot_car_params(FakeParams({
    "StarPilotCarParamsPersistent": b"not-capnp",
  })) is None


def test_corrupt_ephemeral_cache_falls_back_to_persistent_params():
  persistent = car.CarParams.new_message()
  persistent.brand = "hyundai"
  persistent.carFingerprint = "KIA_EV9"
  cached = load_cached_car_params(FakeParams({
    "CarParamsCache": b"not-capnp",
    "CarParamsPersistent": persistent.to_bytes(),
  }))
  assert cached is not None
  assert cached.brand == "hyundai"
  assert str(cached.carFingerprint) == "KIA_EV9"


def test_valid_starpilot_cache_round_trips():
  persistent = custom.StarPilotCarParams.new_message()
  cached = load_cached_starpilot_car_params(FakeParams({
    "StarPilotCarParamsPersistent": persistent.to_bytes(),
  }))
  assert cached is not None


def test_stale_cached_ev9_starpilot_safety_is_canonicalized():
  cached_params = car.CarParams.new_message(carFingerprint="KIA_EV9")
  safety = cached_params.init("safetyConfigs", 1)
  safety[0].safetyModel = car.CarParams.SafetyModel.hyundaiCanfdEv9
  safety[0].safetyParam = 0x495
  cached_starpilot_params = custom.StarPilotCarParams.new_message()
  cached_starpilot_params.init("safetyConfigs", 1)[0].safetyParam = 0x8C95

  normalized = normalize_ev9_cached_starpilot_safety(cached_params, cached_starpilot_params)

  assert normalized is not None
  assert normalized.safetyConfigs[0].safetyParam == 0xC95


def test_incompatible_cached_ev9_starpilot_safety_is_rejected():
  cached_params = car.CarParams.new_message(carFingerprint="KIA_EV9")
  safety = cached_params.init("safetyConfigs", 1)
  safety[0].safetyModel = car.CarParams.SafetyModel.hyundaiCanfdEv9
  safety[0].safetyParam = 0x495

  assert normalize_ev9_cached_starpilot_safety(
    cached_params, custom.StarPilotCarParams.new_message(),
  ) is None


def test_wrong_vehicle_cache_cannot_adopt_live_ev9_owner():
  clean = (EV9PandaPreinitFlags.IDENTITY_VALID |
           EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
           EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  status = SimpleNamespace(valid=True, version=4, state=int(EV9PandaPreinitState.ACTIVE),
                           flags=int(clean), communicationType=1, timingValid=True)
  update_ev9_panda_preinit_handoff([SimpleNamespace(ev9LongPreinitStatus=status)])
  wrong = SimpleNamespace(brand="hyundai", carFingerprint="HYUNDAI_IONIQ_6", carFw=[],
                          openpilotLongitudinalControl=True, pcmCruise=False)
  params = FakeParams({
    "EV9LongPreinitPanda": True,
    "OpenpilotEnabledToggle": True,
    "AlphaLongitudinalEnabled": True,
  })
  assert not attempt_ev9_pre_fingerprint_suppression(wrong, params)


def test_fresh_revalidation_rejects_active_to_restoring_transition():
  clean = (EV9PandaPreinitFlags.IDENTITY_VALID |
           EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
           EV9PandaPreinitFlags.BRIDGE_ACTIVE)
  active = SimpleNamespace(valid=True, version=4, state=int(EV9PandaPreinitState.ACTIVE),
                           flags=int(clean), communicationType=1, timingValid=True)
  update_ev9_panda_preinit_handoff([SimpleNamespace(ev9LongPreinitStatus=active)])

  restoring = SimpleNamespace(
    valid=True,
    version=4,
    state=int(EV9PandaPreinitState.RESTORING),
    flags=int(EV9PandaPreinitFlags.RESTORE_SENT | EV9PandaPreinitFlags.DEADLINE_MISSED),
    communicationType=1,
    timingValid=True,
  )

  class FakeSubMaster:
    updated = {"pandaStates": False}
    update_calls = 0

    def update(self, timeout_ms):
      assert 0 < timeout_ms <= 250
      self.update_calls += 1
      # An unrelated high-rate service can wake SubMaster first. Revalidation
      # must keep polling until pandaStates itself is fresh.
      self.updated["pandaStates"] = self.update_calls >= 2

    def __getitem__(self, service):
      assert service == "pandaStates"
      return [SimpleNamespace(ev9LongPreinitStatus=restoring)]

  sm = FakeSubMaster()
  handoff = revalidate_ev9_panda_preinit_handoff(sm)
  assert sm.update_calls == 2
  assert handoff.owner == EV9PandaPreinitOwner.PANDA_PENDING
  assert handoff.knockout_owned
  assert handoff.host_uds_veto
  assert not handoff.adoptable


def test_invalid_resident_status_vetoes_host_uds_without_becoming_adoptable():
  invalid = SimpleNamespace(resident=True, valid=False)
  handoff = update_ev9_panda_preinit_handoff([SimpleNamespace(ev9LongPreinitStatus=invalid)])

  assert handoff.owner == EV9PandaPreinitOwner.FAILED
  assert handoff.resident
  assert not handoff.sample_valid
  assert handoff.host_uds_veto
  assert not handoff.adoptable


def test_firmware_queries_require_neither_raw_request_nor_resident_veto():
  no_handoff = update_ev9_panda_preinit_handoff([])
  assert ev9_preinit_allows_fw_query(FakeParams(), no_handoff)
  assert not ev9_preinit_allows_fw_query(FakeParams({"EV9LongPreinitPanda": True}), no_handoff)

  invalid = SimpleNamespace(resident=True, valid=False)
  resident_handoff = update_ev9_panda_preinit_handoff([SimpleNamespace(ev9LongPreinitStatus=invalid)])
  assert not ev9_preinit_allows_fw_query(FakeParams(), resident_handoff)


def _valid_canfd(address: int, bus: int, length: int, counter: int, returned: bool = True) -> CanData:
  dat = bytearray(length)
  dat[2] = counter
  crc = hyundaicanfd.hkg_can_fd_checksum(address, None, dat)
  dat[0] = crc & 0xFF
  dat[1] = crc >> 8
  return CanData(address, bytes(dat), bus + (0x80 if returned else 0))


def _claim_templates() -> dict[tuple[int, int], CanData]:
  return {
    key: _valid_canfd(key[1], key[0], length, index, returned=False)
    for index, (key, (length, _)) in enumerate(EV9_PREINIT_MANAGED_FRAMES.items())
  }


def test_takeover_baselines_require_complete_fresh_resident_receipts():
  messages = [
    _valid_canfd(address, bus, length, index)
    for index, ((bus, address), (length, _)) in enumerate(EV9_PREINIT_MANAGED_FRAMES.items())
  ]
  # Physical and rejected copies are never allowed to overwrite the resident snapshot.
  messages.extend([
    _valid_canfd(0x100, 0, 24, 0xEE, returned=False),
    CanData(0x100, messages[0].dat, 0xC0),
  ])
  baselines = {}
  collect_ev9_preinit_baselines(baselines, messages, 10.0)
  complete = complete_ev9_preinit_baselines(baselines, 10.01)

  assert complete is not None
  assert len(complete) == len(EV9_PREINIT_MANAGED_FRAMES)
  assert complete[0].src == 0
  assert complete[0].dat[2] == 0
  assert complete_ev9_preinit_baselines(baselines, 10.16) is None


def test_takeover_claim_requires_every_hardware_returned_receipt():
  messages = [
    _valid_canfd(address, bus, length, index)
    for index, ((bus, address), (length, _)) in enumerate(EV9_PREINIT_MANAGED_FRAMES.items())
  ]
  messages.append(CanData(0x730, b"\x02\x3e\x80".ljust(8, b"\x00"), 0x81))
  receipts = set()
  collect_ev9_preinit_claim_receipts(receipts, messages)
  assert complete_ev9_preinit_claim_receipts(receipts)

  receipts.remove((1, 0x730))
  assert not complete_ev9_preinit_claim_receipts(receipts)
  collect_ev9_preinit_claim_receipts(
    receipts, [CanData(0x730, b"\x02\x3e\x80".ljust(8, b"\x00"), 0xC1)],
  )
  assert not complete_ev9_preinit_claim_receipts(receipts)


def test_takeover_claim_retries_fill_all_managed_streams_without_duplicates():
  templates = _claim_templates()
  messages = []
  assert ensure_ev9_preinit_claim_retries(messages, templates)

  assert [(msg.src, msg.address) for msg in messages] == [*EV9_PREINIT_MANAGED_FRAMES, (1, 0x730)]
  assert messages[:-1] == list(templates.values())
  assert messages[-1].dat == b"\x02\x3e\x80".ljust(8, b"\x00")

  assert ensure_ev9_preinit_claim_retries(messages, templates)
  assert [(msg.src, msg.address) for msg in messages] == [*EV9_PREINIT_MANAGED_FRAMES, (1, 0x730)]


def test_takeover_claim_retry_prefers_fresh_exact_ci_body_and_caches_it():
  templates = _claim_templates()
  fresh = bytearray(templates[(1, 0x345)].dat)
  fresh[3] ^= 0x80
  generated = CanData(0x345, bytes(fresh), 1)
  messages = [generated]

  assert ensure_ev9_preinit_claim_retries(messages, templates)
  assert templates[(1, 0x345)] == generated
  assert sum((msg.src, msg.address) == (1, 0x345) for msg in messages) == 1
  assert next(msg for msg in messages if (msg.src, msg.address) == (1, 0x345)) == generated
  assert messages[-1].dat == b"\x02\x3e\x80".ljust(8, b"\x00")

  assert ensure_ev9_preinit_claim_retries(messages, templates)
  for key in EV9_PREINIT_MANAGED_FRAMES:
    assert sum((msg.src, msg.address) == key for msg in messages) == 1
  assert sum(msg.src == 1 and msg.address == 0x730 for msg in messages) == 1


def test_takeover_claim_retry_requires_exact_managed_tuple():
  templates = _claim_templates()
  messages = [
    CanData(0x1DA, b"\x00" * 8, 1),
    CanData(0x730, b"\x03\x19\x02\xff".ljust(8, b"\x00"), 1),
  ]
  assert ensure_ev9_preinit_claim_retries(messages, templates)

  exact = [(msg.src, msg.address, len(msg.dat)) for msg in messages]
  assert exact[:2] == [(1, 0x1DA, 8), (1, 0x730, 8)]
  assert exact[2:] == [(bus, address, length) for (bus, address), (length, _) in EV9_PREINIT_MANAGED_FRAMES.items()] + \
    [(1, 0x730, 8)]
  assert messages[-1].dat == b"\x02\x3e\x80".ljust(8, b"\x00")


def test_takeover_claim_retry_fails_closed_on_incomplete_or_malformed_templates():
  templates = _claim_templates()
  incomplete = dict(templates)
  incomplete.pop((1, 0x345))
  messages = []
  assert not ensure_ev9_preinit_claim_retries(messages, incomplete)
  assert messages == []

  malformed = dict(templates)
  malformed[(1, 0x345)] = CanData(0x345, b"\x00" * 7, 1)
  assert not ensure_ev9_preinit_claim_retries(messages, malformed)
  assert messages == []


def test_preinit_parser_packets_restore_timestamp_envelope():
  packets = [[CanData(0x100, b"\x00" * 24, 0)], [CanData(0x12A, b"\x00" * 16, 1)]]
  assert ev9_preinit_parser_packets(packets, 1.25) == [(1_250_000_000, packets[0]), (1_250_000_000, packets[1])]


def test_recovered_fault_dwell_boundary():
  assert ev9_preinit_recovered_fault_dwell_complete(False, None, 0.0)
  assert not ev9_preinit_recovered_fault_dwell_complete(True, None, 10.0)
  assert not ev9_preinit_recovered_fault_dwell_complete(True, 10.0, 12.249)
  assert ev9_preinit_recovered_fault_dwell_complete(True, 10.0, 12.25)


def test_takeover_safety_gate_requires_exact_clean_hyundai_state():
  status = SimpleNamespace(resident=True, timingValid=True)
  can_state = SimpleNamespace(
    busOff=False, errorWarning=False, errorPassive=False, canCoreResetCnt=0, busOffCnt=0,
    receiveErrorCnt=0, transmitErrorCnt=0, totalErrorCnt=0,
    totalTxLostCnt=0, totalRxLostCnt=0, irq0CallRate=1000, irq1CallRate=150,
  )
  values = {
    "ev9LongPreinitStatus": status,
    "safetyModel": "hyundaiCanfd",
    "safetyParam": 0xA5,
    "alternativeExperience": 32,
    "faultStatus": "none",
    "faults": [],
    "interruptLoad": 0.37,
    "heartbeatLost": False,
    "safetyRxChecksInvalid": False,
    "safetyRxInvalid": 0,
    "safetyTxBlocked": 0,
    "rxBufferOverflow": 0,
    "txBufferOverflow": 0,
    "canState0": can_state,
    "canState1": can_state,
    "canState2": can_state,
  }
  panda_state = SimpleNamespace(**values)
  assert ev9_preinit_safety_ready([panda_state], "hyundaiCanfd", 0xA5, 32)

  recovered_values = values | {"faultStatus": "faultTemp", "faults": ["interruptRateCan3"]}
  recovered = SimpleNamespace(**recovered_values)
  assert ev9_preinit_panda_fault_recovered(recovered)
  assert ev9_preinit_panda_fault_acceptable(recovered)
  assert ev9_preinit_safety_ready([recovered], "hyundaiCanfd", 0xA5, 32)

  historical = SimpleNamespace(**(values | {"faultStatus": "faultTemp", "faults": []}))
  assert ev9_preinit_panda_fault_acceptable(historical)
  assert ev9_preinit_safety_ready([historical], "hyundaiCanfd", 0xA5, 32)
  malformed_permanent = SimpleNamespace(**(values | {"faultStatus": "faultPerm", "faults": []}))
  assert not ev9_preinit_panda_fault_acceptable(malformed_permanent)
  assert not ev9_preinit_safety_ready([malformed_permanent], "hyundaiCanfd", 0xA5, 32)

  for irq0, irq1, interrupt_load in ((0, 0, 0.1), (8000, 1, 0.1), (1, 8000, 0.1), (1, 1, 0.75)):
    can3 = SimpleNamespace(**(vars(can_state) | {"irq0CallRate": irq0, "irq1CallRate": irq1}))
    bad = SimpleNamespace(**(recovered_values | {"canState2": can3, "interruptLoad": interrupt_load}))
    assert not ev9_preinit_panda_fault_recovered(bad)
    assert not ev9_preinit_safety_ready([bad], "hyundaiCanfd", 0xA5, 32)

  for fault_status, faults in (("faultPerm", ["interruptRateCan3"]),
                               ("faultTemp", ["interruptRateCan2"]),
                               ("faultTemp", ["interruptRateCan3", "interruptRateCan2"])):
    bad = SimpleNamespace(**(values | {"faultStatus": fault_status, "faults": faults}))
    assert not ev9_preinit_panda_fault_acceptable(bad)
    assert not ev9_preinit_safety_ready([bad], "hyundaiCanfd", 0xA5, 32)

  for key, bad_value in (
    ("safetyModel", "elm327"), ("safetyParam", 0xA1),
    ("safetyRxChecksInvalid", True), ("heartbeatLost", True),
  ):
    bad = SimpleNamespace(**(values | {key: bad_value}))
    assert not ev9_preinit_safety_ready([bad], "hyundaiCanfd", 0xA5, 32)

  bad_bus = SimpleNamespace(**vars(can_state))
  bad_bus.errorPassive = True
  bad = SimpleNamespace(**(values | {"canState1": bad_bus}))
  assert not ev9_preinit_safety_ready([bad], "hyundaiCanfd", 0xA5, 32)

  historical_bus = SimpleNamespace(**vars(can_state))
  historical_bus.busOffCnt = 3
  historical_bus.totalErrorCnt = 8
  historical_bus.totalTxLostCnt = 2
  historical = SimpleNamespace(**(values | {
    "rxBufferOverflow": 4, "txBufferOverflow": 5, "safetyTxBlocked": 7, "canState2": historical_bus,
  }))
  assert ev9_preinit_safety_ready([historical], "hyundaiCanfd", 0xA5, 32)

  baseline = ev9_preinit_health_snapshot([historical])
  assert ev9_preinit_health_unchanged([historical], baseline)
  changed = SimpleNamespace(**(vars(historical) | {"txBufferOverflow": 6}))
  assert not ev9_preinit_health_unchanged([changed], baseline)
  safety_blocked = SimpleNamespace(**(vars(historical) | {"safetyTxBlocked": 8}))
  assert not ev9_preinit_health_unchanged([safety_blocked], baseline)
  reset_bus = SimpleNamespace(**(vars(historical_bus) | {"canCoreResetCnt": 1}))
  reset = SimpleNamespace(**(vars(historical) | {"canState2": reset_bus}))
  assert not ev9_preinit_health_unchanged([reset], baseline)


def test_expected_safety_rejection_accepts_bounded_async_exact_angle_receipts():
  status = SimpleNamespace(resident=True)
  can_state = SimpleNamespace(
    canCoreResetCnt=0, busOffCnt=0, totalErrorCnt=0, totalTxLostCnt=0, totalRxLostCnt=0,
  )

  def panda(blocked=0, overflow=0):
    return SimpleNamespace(
      ev9LongPreinitStatus=status, rxBufferOverflow=overflow, txBufferOverflow=0,
      safetyTxBlocked=blocked, canState0=can_state, canState1=can_state, canState2=can_state,
    )

  baseline = ev9_preinit_health_snapshot([panda()])
  candidate_four = ev9_preinit_health_snapshot([panda(blocked=4)])
  candidate_five = ev9_preinit_health_snapshot([panda(blocked=5)])
  active_cb = bytearray(24)
  active_cb[3] = 0x20
  rejected = [(1.0 + i * 0.01, CanData(0xCB, bytes(active_cb), 0xC1)) for i in range(5)]
  # Route 1a6 published +4 while the fifth receipt was already queued, then +5.
  assert ev9_preinit_expected_safety_rejection([panda(blocked=4)], baseline, rejected) == candidate_four
  assert ev9_preinit_expected_safety_rejection([panda(blocked=5)], baseline, rejected) == candidate_five
  assert ev9_preinit_expected_safety_rejection([panda(blocked=6)], baseline, rejected) is None
  assert ev9_preinit_expected_safety_rejection([panda(blocked=9)], baseline, rejected) is None
  assert ev9_preinit_expected_safety_rejection([panda(blocked=4, overflow=1)], baseline, rejected) is None
  assert ev9_preinit_expected_safety_rejection(
    [panda(blocked=4)], baseline,
    rejected[:-1] + [(1.04, CanData(0x1A0, bytes(32), 0xC1))],
  ) is None
  inactive_cb = bytearray(active_cb)
  inactive_cb[3] = 0x10
  candidate_one = ev9_preinit_health_snapshot([panda(blocked=1)])
  assert ev9_preinit_expected_safety_rejection(
    [panda(blocked=1)], baseline, [(1.0, CanData(0xCB, bytes(inactive_cb), 0xC1))],
  ) == candidate_one
  route_1a7 = [
    bytes.fromhex(body) for body in (
      "a02081109530000000000000000000000000000000000000",
      "1a4881107430000000000000000000000000000000000000",
      "6f4f81105530000000000000000000000000000000000000",
      "98f081103530000000000000000000000000000000000000",
    )
  ]
  route_1a7_rejected = [(1.0 + i * 0.01, CanData(0xCB, body, 0xC1)) for i, body in enumerate(route_1a7)]
  assert ev9_preinit_expected_safety_rejection(
    [panda(blocked=3)], baseline, route_1a7_rejected,
  ) == ev9_preinit_health_snapshot([panda(blocked=3)])
  assert ev9_preinit_expected_safety_rejection(
    [panda(blocked=4)], baseline, route_1a7_rejected,
  ) == candidate_four
  malformed_cb = bytearray(inactive_cb)
  malformed_cb[6] = 1
  assert ev9_preinit_expected_safety_rejection(
    [panda(blocked=1)], baseline, [(1.0, CanData(0xCB, bytes(malformed_cb), 0xC1))],
  ) is None


def test_rejected_output_receipts_are_bounded_and_keep_only_panda_rejections():
  active_cb = bytearray(24)
  active_cb[3] = 0x20
  recent = [(1.0, CanData(0xCB, bytes(active_cb), 0xC1))]
  collect_ev9_preinit_rejected_outputs(recent, [
    CanData(0xCB, bytes(active_cb), 0x81),
    CanData(0xCB, bytes(active_cb), 0xC1),
  ], 2.01)
  assert [(msg.src, msg.address) for _, msg in recent] == [(0xC1, 0xCB)]


def test_recovered_fault_history_rejects_new_or_reappearing_faults():
  status = SimpleNamespace(resident=True)
  clean = SimpleNamespace(ev9LongPreinitStatus=status, faultStatus="none", faults=[])
  historical = SimpleNamespace(ev9LongPreinitStatus=status, faultStatus="faultTemp", faults=[])
  recovered = SimpleNamespace(ev9LongPreinitStatus=status, faultStatus="faultTemp",
                              faults=["interruptRateCan3"])
  other = SimpleNamespace(ev9LongPreinitStatus=status, faultStatus="faultTemp",
                          faults=["interruptRateCan2"])

  history = EV9PreinitFaultHistory()
  assert history.update([recovered], initialize=True)
  assert history.recovered_fault_allowed
  assert history.recovered_fault_authorized
  assert history.update([recovered])
  assert history.update([clean])
  assert history.recovered_fault_cleared
  assert not history.recovered_fault_authorized
  assert history.update([historical])
  assert not history.update([recovered])

  clean_history = EV9PreinitFaultHistory()
  assert clean_history.update([clean], initialize=True)
  assert clean_history.update([historical])
  assert not clean_history.update([recovered])

  unsupported_history = EV9PreinitFaultHistory()
  assert not unsupported_history.update([other], initialize=True)


def test_timing_read_failure_vetoes_uds_without_adoptable_handoff():
  flags = (EV9PandaPreinitFlags.IDENTITY_VALID |
           EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED |
           EV9PandaPreinitFlags.BRIDGE_ACTIVE |
           EV9PandaPreinitFlags.HOST_HANDOFF)
  status = SimpleNamespace(
    resident=True, valid=True, version=4, state=int(EV9PandaPreinitState.HANDOFF),
    flags=int(flags), communicationType=1, timingValid=False,
  )
  handoff = update_ev9_panda_preinit_handoff([SimpleNamespace(ev9LongPreinitStatus=status)])
  assert handoff.owner == EV9PandaPreinitOwner.PANDA_PENDING
  assert handoff.host_uds_veto
  assert not handoff.adoptable
