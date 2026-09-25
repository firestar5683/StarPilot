"""Default Volt STOP ownership, qualified release, and parsed Controls-to-CAN recurrence."""
from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from opendbc.car import Bus
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.longitudinal import VoltStopEvidence, volt_policy_for
from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.vehicle_model import VehicleModel
from opendbc.can import CANPacker
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.tests.test_gm_euv_long_policy import interp
from openpilot.starpilot.longitudinal.tests.test_gm_volt_cc_policy import fixture, physical_frames
from openpilot.starpilot.longitudinal.tests.test_gm_volt_long_policy import controls_fixture, observed_lead, state


def profiles():
  for candidate, accelerator, sascm in ((CAR.CHEVROLET_VOLT, True, False),
                                       (CAR.CHEVROLET_VOLT, False, False),
                                       (CAR.CHEVROLET_VOLT_ASCM, True, True)):
    for alpha in (False, True):
      yield ordinary_params(candidate, alpha=alpha, accelerator=accelerator, sascm=sascm, radar=True), accelerator, sascm, alpha


def original_stop(output, speed, target, gateway, brake=False):
  floor, rate, minimum = (-1.5, 3., 1.75) if gateway else (-.25, 1., 1.5)
  if output > floor:
    output = min(output, 0.) - rate * .01
  if not brake and speed > minimum and target < output - .25:
    output = max(target, output - interp(speed, [minimum, 3., 6., 10.], [.02, .03, .05, .07]))
  return min(max(output, -4.), 2.)


def original_brake(accel, speed, cp):
  drag = .5 * .30 * (1.05 * cp.wheelbase + .0679) * 1.225 * speed ** 2 / cp.mass
  threshold = interp(speed, [1.29, 1.52, 1.55, 1.6, 1.7, 1.8, 2., 2.2, 2.5, 5.52, 9.6, 20.5, 23.5, 35.],
                     [0., -.14, -.16, -.18, -.215, -.255, -.32, -.41, -.5, -.72, -.895, -1.125, -1.145, -1.16])
  return round(interp(min(max(accel + drag, -4.), 2.), [-4., threshold], [400., 0.]))


def brake_wire(brake, counter, full_stop=False):
  mode = (13 if full_stop else 10) if brake else 1
  raw = (4096 - brake) & 4095
  checksum = (65536 - (mode << 12) - raw - counter) & 65535
  return bytes([(mode << 4) | (raw >> 8), raw & 255, checksum >> 8, checksum & 255, counter])


class TestVoltStop(unittest.TestCase):
  def test_actual_constructor_services_and_exact_final_owner(self):
    class Registered(Exception):
      pass
    for cp, _, sascm, alpha in profiles():
      selected = not sascm or alpha
      owner = volt_policy_for(cp)
      self.assertEqual(owner is not None, selected)
      if selected:
        self.assertEqual((owner.stopping_decel_rate, owner.starting_speed, cp.stopAccel),
                         (1., .25, -.25) if sascm else (3., .75, -1.5))
      captured = {}
      def register(services, output=captured, **options):
        output.update(services=services, options=options)
        raise Registered
      with patch('openpilot.selfdrive.controls.controlsd.Params'), \
           patch('openpilot.selfdrive.controls.controlsd.messaging.log_from_bytes', return_value=cp), \
           patch('openpilot.selfdrive.controls.controlsd.read_selection', return_value=NS(policy=None)), \
           patch('openpilot.selfdrive.controls.controlsd.learning_allowed', return_value=False), \
           patch('openpilot.selfdrive.controls.controlsd.feature_enabled', return_value=False), \
           patch('openpilot.starpilot.longitudinal.inputs.toyota_development_enabled', return_value=False), \
           patch('openpilot.selfdrive.controls.controlsd.messaging.SubMaster', side_effect=register):
        with self.assertRaises(Registered):
          Controls()
      for name in ('radarState', 'deviceState'):
        self.assertEqual(name in captured['services'], selected)

  def test_stop_recurrence_and_release_boundaries(self):
    for cp, _, sascm, alpha in profiles():
      if sascm and not alpha:
        continue
      for speed in (0., .25, .75, 1.5, 1.75, 6., 10.):
        long = LongControl(cp)
        wanted = 0.
        for tick in range(100):
          evidence = VoltStopEvidence(1, 1_000_000_000 + tick * 10_000_000, False)
          wanted = original_stop(wanted, speed, -2., not sascm)
          output = long.update(True, state(speed), -2., True, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=evidence))
          self.assertAlmostEqual(output, wanted, places=7)
      for target, lead, still, count in ((.15, False, False, 40), (.2, False, True, 35),
                                       (.2, True, True, 1), (.45, False, False, 1)):
        long = LongControl(cp)
        cs = state(0.)
        cs.cruiseState.standstill = still
        long.update(True, cs, 0., True, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_000_000_000, lead)))
        for tick in range(1, count + 1):
          long.update(True, cs, target, False, (-4., 2.),
            context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_000_000_000 + tick * 10_000_000, lead)))
          expected = 'pid' if target > .15 and tick >= count else 'stopping'
          self.assertEqual({0: 'off', 1: 'pid', 2: 'stopping', 3: 'starting'}[int(long.long_control_state)], expected)

  def test_exact_start_speed_and_twenty_ms_continuity_boundary(self):
    for cp, _, sascm, alpha in profiles():
      if sascm and not alpha:
        continue
      threshold = .25 if sascm else .75
      for speed in (threshold, threshold + .000001):
        long = LongControl(cp)
        cs = state(speed)
        cs.cruiseState.standstill = True
        long.update(True, cs, 0., True, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_000_000_000, False)))
        long.update(True, cs, .1, False, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_010_000_000, False)))
        self.assertEqual(int(long.long_control_state), 1 if speed > threshold else 2)
      for gap, expected in ((20_000_000, 1), (20_000_001, 2)):
        long = LongControl(cp)
        cs = state(0.)
        cs.cruiseState.standstill = True
        long.update(True, cs, 0., True, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_000_000_000, False)))
        for tick in range(1, 34):
          long.update(True, cs, .2, False, (-4., 2.),
            context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_000_000_000 + tick * 10_000_000, False)))
        long.update(True, cs, .2, False, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, 1_330_000_000 + gap, False)))
        self.assertEqual(int(long.long_control_state), expected)

  def test_missing_evidence_overrides_and_continuity_reset(self):
    for cp, _, sascm, alpha in profiles():
      if sascm and not alpha:
        continue
      for interruption in ('missing', 'drive', 'gap', 'brake', 'gas'):
        long = LongControl(cp)
        cs = state(0.)
        cs.cruiseState.standstill = True
        now = 1_000_000_000
        long.update(True, cs, 0., True, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, now, False)))
        for tick in range(1, 35):
          long.update(True, cs, .2, False, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(1, now + tick * 10_000_000, False)))
        now += 350_000_000
        drive = 2 if interruption == 'drive' else 1
        if interruption == 'gap':
          now += 10_000_001
        cs.brakePressed, cs.gasPressed = interruption == 'brake', interruption == 'gas'
        evidence = None if interruption == 'missing' else VoltStopEvidence(drive, now, False)
        long.update(True, cs, .2, False, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=evidence))
        self.assertEqual(int(long.long_control_state), 2)
        cs.brakePressed = cs.gasPressed = False
        for tick in range(1, 35):
          long.update(True, cs, .2, False, (-4., 2.),
            context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(drive, now + tick * 10_000_000, False)))
          if tick < 34 or interruption in ('missing', 'brake', 'gas'):
            self.assertEqual(int(long.long_control_state), 2)
        long.update(False, cs, .5, False, (-4., 2.), context=LongitudinalContext(vehicle_stop_evidence=VoltStopEvidence(drive, now + 350_000_000, False)))
        self.assertEqual((int(long.long_control_state), long.last_output_accel), (0, 0.))

  def test_controls_transport_admission_does_not_guess_lead(self):
    for defect in ('stale_radar', 'stale_plan', 'invalid_car', 'previous_drive', 'lead_disagreement'):
      controls, now, offset = controls_fixture()
      with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + offset)):
        self.assertFalse(controls.longitudinal_inputs._gm_volt_stop_from_observation(controls.longitudinal_inputs._gm_volt_observation()).has_lead)
        if defect == 'stale_radar':
          controls.sm.logMonoTime['radarState'] = now - 200_000_000
        elif defect == 'stale_plan':
          controls.sm.logMonoTime['longitudinalPlan'] = now - 200_000_000
        elif defect == 'invalid_car':
          controls.sm['carState'].canValid = False
        elif defect == 'previous_drive':
          controls.sm['deviceState'].startedMonoTime = now - 1_000_000
        else:
          controls.sm['longitudinalPlan'].hasLead = True
          # Existing PID no-lead transport contract is unchanged by stop agreement.
          self.assertFalse(observed_lead(controls))
        self.assertIsNone(controls.longitudinal_inputs._gm_volt_stop_from_observation(controls.longitudinal_inputs._gm_volt_observation()))

  def test_primary_plan_agreement_does_not_reject_secondary_lead(self):
    for primary in (False, True):
      for secondary in (False, True):
        for plan_lead in (False, True):
          controls, now, offset = controls_fixture()
          controls.sm['radarState'].leadOne.present = primary
          controls.sm['radarState'].leadTwo.present = secondary
          controls.sm['longitudinalPlan'].hasLead = plan_lead
          with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + offset)):
            observation = controls.longitudinal_inputs._gm_volt_observation()
            self.assertEqual(observation[0], primary or secondary)
            evidence = controls.longitudinal_inputs._gm_volt_stop_from_observation(observation)
          if plan_lead == primary:
            self.assertIs(evidence.has_lead, primary)
          else:
            self.assertIsNone(evidence)

  def test_parsed_controls_card_moving_stop_wire(self):
    for cp, accelerator, sascm, alpha in profiles():
      if sascm and not alpha:
        continue
      controls, card, _, _, sent, base, _ = fixture(alpha)
      ci = CarInterface(cp)
      controls.CP, controls.CI, controls.LoC, controls.VM = cp, ci, LongControl(cp), VehicleModel(cp)
      controls.longitudinal_inputs.gm_cc_enabled = controls.longitudinal_inputs.gm_start_enabled = controls.longitudinal_inputs.gm_euv_enabled = False
      controls.longitudinal_inputs.gm_volt_enabled = True
      controls.longitudinal_inputs.gm_volt_boot_offset_ns, controls.longitudinal_inputs.gm_volt_source_floor_ns = 0, base - 500_000_000
      log = messaging.new_message('controlsState').controlsState.lateralControlState.init(cp.lateralTuning.which() + 'State')
      controls.LaC = NS(reset=lambda: None, update=lambda *args, log=log: (0., 0., log))
      card.CP, card.CI, card.volt_cc_selected = cp, ci, False
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      wanted = 0.
      for tick in range(-2, 152):
        now = base + tick * 10_000_000
        speed = 6. if tick < 64 else 0.
        frames = physical_frames(packer, speed=speed, gear=4, counter=tick % 4)
        if not accelerator:
          frames.append(packer.make_can_msg('EBCMBrakePedalPosition', 0, {}))
        frames += [packer.make_can_msg(name, 2, {}) for name in ('ASCMLKASteeringCmd', 'AEBCmd', 'ASCMActiveCruiseControlStatus')]
        out = ci.update([(now - 2_000_000, frames)])
        if tick < 0:
          continue
        self.assertTrue(out.canValid)
        controls.sm.data['carState'] = out
        plan = controls.sm['longitudinalPlan']
        target = -2. if tick < 104 else .1 if tick < 149 else .5
        plan.aTarget, plan.shouldStop, plan.hasLead = target, tick < 104, False
        for name in controls.sm.logMonoTime:
          controls.sm.logMonoTime[name] = now - 2_000_000
          controls.sm.recv_time[name] = (now - 1_000_000) / 1e9
        prior = {0: 'off', 1: 'pid', 2: 'stopping', 3: 'starting'}[int(controls.LoC.long_control_state)]
        with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)), \
             patch('openpilot.selfdrive.car.card.time.monotonic', return_value=now / 1e9), \
             patch('openpilot.selfdrive.car.card.REPLAY', False):
          self.assertFalse(controls.longitudinal_inputs._gm_volt_stop_from_observation(controls.longitudinal_inputs._gm_volt_observation()).has_lead)
          with patch.object(controls.longitudinal_inputs, '_gm_volt_observation', wraps=controls.longitudinal_inputs._gm_volt_observation) as observation:
            cc, lateral = controls.state_control()
          self.assertEqual(observation.call_count, 1)
          controls.publish(cc, lateral)
          controls.sm.data['carControl'] = cc
          for mapping in (controls.sm.seen, controls.sm.alive, controls.sm.valid):
            mapping['carControl'] = True
          controls.sm.logMonoTime['carControl'] = now - 2_000_000
          controls.sm.recv_time['carControl'] = (now - 1_000_000) / 1e9
          card.controls_update(out, cc.as_reader())
        if tick < 149:
          wanted = original_stop(wanted, out.vEgo, target, not sascm) if tick < 104 else min(wanted, cp.stopAccel)
          self.assertAlmostEqual(cc.actuators.accel, wanted, places=6)
          self.assertEqual(int(controls.LoC.long_control_state), 2)
        else:
          self.assertEqual(int(controls.LoC.long_control_state), 1)
        self.assertEqual(str(cc.actuators.longControlState), prior)
        if 0 < tick < 149 and tick % 4 == 0:
          counter = (tick // 4) % 4
          full_stop = bool(out.standstill)
          gas = bytes([1 | (counter << 6), 0x62 if full_stop else 0x42, 0xab, 0xe0, 0,
                       0x9d if full_stop else 0xbd, 0x54, 0x20 - counter])
          near_stop = abs(out.vEgo) < (.25 if sascm else .5)
          brake = round(-100 * cp.stopAccel) if near_stop else original_brake(float(cc.actuators.accel), out.vEgo, cp)
          bus = 0 if sascm or not accelerator else 2
          wire = [(msg[0], bytes(msg[1]), msg[2]) for msg in sent[-1][0] if msg[0] in (0x2cb, 0x315)]
          self.assertEqual(wire, [(0x2cb, gas, 0), (0x315, brake_wire(brake, counter, full_stop), bus)])
