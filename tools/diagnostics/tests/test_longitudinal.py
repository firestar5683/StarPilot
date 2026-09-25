import math
from types import SimpleNamespace as NS
import unittest

from tools.diagnostics.longitudinal import analyze


class Event:
  def __init__(self, service, seconds, **fields):
    self.service = service
    self.logMonoTime = int(seconds * 1e9)
    self.valid = True
    setattr(self, service, NS(**fields))

  def which(self):
    return self.service


def cluster(t, *, target=1.0, command=0.5, ego=0.2, source="cruise", experimental=False,
            active=True, gas=False, brake=False):
  return [Event("carState", t, aEgo=ego, gasPressed=gas, brakePressed=brake),
          Event("selfdriveState", t, experimentalMode=experimental),
          Event("longitudinalPlan", t, aTarget=target, longitudinalPlanSource=source),
          Event("carControl", t, longActive=active, actuators=NS(accel=command))]


class TestLongitudinalTrace(unittest.TestCase):
  def test_continuous_same_mode_rates_are_signal_derivatives(self):
    messages = cluster(1) + cluster(1.1, target=1.2, command=0.6, ego=0.3) + cluster(1.2, target=1.4, command=0.7, ego=0.4)
    report = analyze(messages)
    command = report["signals"]["commandAccel"]
    self.assertEqual(command["continuousFrameDeltaSeconds"]["sampleCount"], 2)
    self.assertAlmostEqual(command["continuousDeltaRateMps3"]["mean"], 1)
    self.assertEqual(report["pedalContextSamples"]["gas=False,brake=False"], 7)

  def test_gap_and_mode_transitions_exclude_derivatives(self):
    messages = cluster(1) + cluster(1.1) + cluster(2, active=False, source="lead0", experimental=True, gas=True)
    report = analyze(messages)
    self.assertEqual(report["transitions"]["source"], 1)
    self.assertEqual(report["transitions"]["experimental"], 1)
    self.assertEqual(report["transitions"]["longActive"], 1)
    self.assertEqual(report["signals"]["commandAccel"]["continuousDeltaRateMps3"]["sampleCount"], 1)
    gap = analyze(cluster(1) + cluster(1.1) + cluster(2))
    self.assertGreater(gap["rejectedPairsOrSamples"]["carControl:gap"], 0)

  def test_nonfinite_missing_and_timestamp_regression_reset_baseline(self):
    messages = cluster(1) + cluster(1.1, command=math.nan) + cluster(1.05) + cluster(1.2)
    report = analyze(messages)
    self.assertEqual(report["signals"]["commandAccel"]["valuesMps2"]["missingCounts"]["missing_or_nonfinite"], 1)
    self.assertGreater(report["rejectedPairsOrSamples"]["carControl:timestamp_regression"], 0)
    self.assertEqual(report["signals"]["commandAccel"]["continuousDeltaRateMps3"]["sampleCount"], 0)

  def test_stale_context_does_not_create_pair(self):
    messages = cluster(1) + [Event("carControl", 2, longActive=True, actuators=NS(accel=1.0))]
    report = analyze(messages)
    self.assertEqual(report["rejectedPairsOrSamples"]["carControl:missing_or_stale_mode"], 1)
    self.assertEqual(report["signals"]["commandAccel"]["continuousFrameDeltaSeconds"]["sampleCount"], 0)

  def test_invalid_envelope_is_excluded(self):
    messages = cluster(1) + cluster(1.1)
    messages[-1].valid = False
    messages.append(Event("longitudinalPlan", 1.15, aTarget=1.0, longitudinalPlanSource="cruise"))
    report = analyze(messages)
    self.assertEqual(report["rejectedPairsOrSamples"]["carControl:invalid_envelope"], 1)
    self.assertEqual(report["rejectedPairsOrSamples"]["longitudinalPlan:missing_or_stale_mode"], 2)
    self.assertEqual(report["signals"]["commandAccel"]["valuesMps2"]["sampleCount"], 1)

  def test_away_and_back_or_invalid_recovery_breaks_other_signal_pair(self):
    baseline = cluster(1) + cluster(1.1)
    toggled = baseline + [Event("selfdriveState", 1.15, experimentalMode=True),
                          Event("selfdriveState", 1.16, experimentalMode=False),
                          Event("longitudinalPlan", 1.2, aTarget=1.4, longitudinalPlanSource="cruise")]
    report = analyze(toggled)
    self.assertEqual(report["transitions"]["experimental"], 2)
    self.assertEqual(report["signals"]["plannerATarget"]["continuousDeltaRateMps3"]["sampleCount"], 0)

    invalid = Event("carControl", 1.15, longActive=True, actuators=NS(accel=0.5))
    invalid.valid = None
    recovered = baseline + [invalid, Event("carControl", 1.16, longActive=True, actuators=NS(accel=0.5)),
                            Event("longitudinalPlan", 1.2, aTarget=1.4, longitudinalPlanSource="cruise")]
    report = analyze(recovered)
    self.assertEqual(report["rejectedPairsOrSamples"]["carControl:invalid_envelope"], 1)
    self.assertEqual(report["signals"]["plannerATarget"]["continuousDeltaRateMps3"]["sampleCount"], 0)
