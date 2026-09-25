import unittest

from opendbc.car.structs import car
from opendbc.car.hyundai.ioniq6_media import MediaObservation, MediaSample
from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings, independent_axis_requested


def state(events=(), valid=True):
  return car.CarState(canValid=valid, gearShifter='drive', buttonEvents=[
    car.CarState.ButtonEvent(type=button, pressed=pressed) for button, pressed in events])


class TestAuxiliaryActions(unittest.TestCase):
  def test_auxiliary_pause_is_not_unqualified_startup_demand(self):
    for action in (3, 4):
      settings = AolSettings(False, 0., 0, 0, (0, 0, 0), (action, 0, 0), (action, 0, 0))
      self.assertFalse(independent_axis_requested(settings))
      self.assertTrue(independent_axis_requested(settings, include_auxiliary=True))
      self.assertFalse(AolCardIntent(settings, explicit_latch=True).auxiliary_supported())

  def test_auxiliary_cannot_rearm_after_actual_gm_fault_owner_update(self):
    from openpilot.starpilot.car.gm.aol import GmAolCardIntent
    for defect in ('permanent', 'event', 'sticky'):
      owner = GmAolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (9, 0, 0)))
      neutral = state()
      neutral.cruiseState.available = True
      owner.update_auxiliary(neutral)
      pressed = state(((car.CarState.ButtonEvent.Type.cancel, True),))
      pressed.cruiseState.available = True
      owner.update(pressed)
      owner.update_auxiliary(pressed)
      released = state(((car.CarState.ButtonEvent.Type.cancel, False),))
      released.cruiseState.available = True
      if defect == 'permanent':
        released.steerFaultPermanent = True
      if defect == 'sticky':
        fault = state()
        fault.cruiseState.available = True
        owner.update(fault, fault_active=True)
      fault_active = True if defect == 'event' else False
      owner.update(released, fault_active=fault_active)
      owner.update_auxiliary(released, fault_active=fault_active)
      self.assertFalse(owner.allowed_latch)

  def test_actual_cancel_short_dispatch_and_invalid_source_reset(self):
    for action, field in ((3, 'pause_lateral'), (4, 'pause_longitudinal'), (9, 'allowed_latch')):
      owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (action, 0, 0)))
      owner.update_auxiliary(state())
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, True),)))
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, False),)))
      self.assertTrue(getattr(owner, field))
      owner.update_auxiliary(state(valid=False))
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, True),)))
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, False),)))
      self.assertTrue(getattr(owner, field))

  def test_actual_media_tracker_and_source_epoch(self):
    owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0), (3, 0, 0), (4, 0, 0)))
    for custom, field in ((False, 'pause_lateral'), (True, 'pause_longitudinal')):
      samples = (MediaSample(False, False, 1), MediaSample(not custom, custom, 100000001),
                 MediaSample(False, False, 200000001))
      owner.update_auxiliary(state(), media=MediaObservation(samples, 200000001, int(custom), True), media_eligible=True)
      self.assertTrue(getattr(owner, field))

  def test_cancel_hold_boundaries_and_unrelated_buttons(self):
    button = car.CarState.ButtonEvent.Type
    for frames, expected in ((1, (True, False, False)), (49, (True, False, False)),
                             (50, (False, True, False)), (249, (False, True, False)),
                             (250, (False, True, True)), (251, (False, True, True))):
      owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (9, 3, 4)))
      owner.update_auxiliary(state())
      for tick in range(frames):
        events = ((button.cancel, True), (button.lkas, True), (button.gapAdjustCruise, True)) if tick == 0 else ()
        source = state(events)
        source.vEgo = 12.
        before = source.to_dict()
        owner.update_auxiliary(source)
        self.assertEqual(source.to_dict(), before)
      owner.update_auxiliary(state(((button.cancel, False), (button.lkas, False), (button.gapAdjustCruise, False))))
      owner.update_auxiliary(state())
      self.assertEqual((owner.allowed_latch, owner.pause_lateral, owner.pause_longitudinal), expected)

  def test_timeout_interrupts_held_cancel(self):
    button = car.CarState.ButtonEvent.Type.cancel
    owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (9, 3, 4)))
    owner.update_auxiliary(state())
    owner.update_auxiliary(state(((button, True),)))
    for _ in range(48):
      owner.update_auxiliary(state())
    interrupted = state()
    interrupted.canTimeout = True
    owner.update_auxiliary(interrupted)
    owner.update_auxiliary(state(((button, False),)))
    self.assertEqual((owner.allowed_latch, owner.pause_lateral, owner.pause_longitudinal), (False, False, False))
    owner.update_auxiliary(state(((button, True),)))
    owner.update_auxiliary(state(((button, False),)))
    self.assertTrue(owner.allowed_latch)

  def test_explicit_owner_auxiliary_actions_denied(self):
    for action in (3, 4, 9):
      owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (action, 0, 0), (action, 0, 0)), explicit_latch=True)
      owner.update_auxiliary(state())
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, True),)))
      owner.update_auxiliary(state(((car.CarState.ButtonEvent.Type.cancel, False),)))
      owner.update_auxiliary(state(), media=MediaObservation((MediaSample(False, False, 1),
        MediaSample(True, False, 100000001), MediaSample(False, False, 200000001)), 200000001, 1, True), media_eligible=True)
      self.assertEqual((owner.allowed_latch, owner.pause_lateral, owner.pause_longitudinal), (False, False, False))


class TestAuxiliaryStartupAdmission(unittest.TestCase):
  def test_actual_cp_master_off_auxiliary_request_is_scoped(self):
    import tempfile
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.gm.interface import CarInterface as GmInterface
    from opendbc.car.gm.values import CAR as GM
    from opendbc.car.honda.interface import CarInterface as HondaInterface
    from opendbc.car.honda.values import CAR as HONDA
    from openpilot.common.params import Params
    from openpilot.starpilot.aol.intent import read_settings
    from openpilot.starpilot.aol.vehicle import policy_for
    from openpilot.starpilot.feature_runtime import enabled, requested

    legacy = GmInterface.get_params(GM.CHEVROLET_BOLT_EUV, gen_empty_fingerprint(), [], False, False, False)
    explicit = HondaInterface.get_params(HONDA.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], False, False, False)
    self.assertTrue(policy_for(legacy).intent_supported)
    self.assertFalse(policy_for(legacy).explicit_latch)
    self.assertTrue(policy_for(explicit).explicit_latch)
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      params.put('AlwaysOnLateral', False, block=True)
      params.put('CancelButtonControl', 3, block=True)
      settings = read_settings(params)
      self.assertFalse(requested(params, 'aol'))
      self.assertTrue(enabled(params, legacy, 'aol', {}))
      self.assertFalse(enabled(params, explicit, 'aol', {}))
      for cp, expected in ((legacy, True), (explicit, False)):
        policy = policy_for(cp)
        self.assertEqual(independent_axis_requested(settings,
          include_auxiliary=policy.intent_supported and not policy.explicit_latch), expected)
