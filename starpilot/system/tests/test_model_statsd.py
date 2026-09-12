import json
from pathlib import Path
from types import SimpleNamespace as NS

from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.model_stats_identity import loaded_identity, output_identity, publish_identity
from openpilot.starpilot.common.tests.test_model_stats import OWNER, totals
from openpilot.starpilot.system.model_statsd import Telemetry


def feed_state(telemetry, t=1, enabled=True, brake=False, accel_button=False, identity=OWNER):
  ns = int(t * 1e9)
  telemetry.feed('deviceState', ns, True, NS(started=True))
  telemetry.feed('carControl', ns, True, NS(latActive=enabled, longActive=enabled))
  telemetry.feed('selfdriveState', ns, True, NS(enabled=enabled))
  telemetry.feed('starpilotCarState', ns, True, NS(alwaysOnLateralEnabled=False, accelPressed=accel_button))
  telemetry.feed('modelV2', ns, True, NS())
  telemetry.feed('starpilotModelV2', ns, True, NS(modelMonoTime=ns, runtimeIdentity=identity))
  return telemetry.feed('carState', ns, True, NS(vEgo=10, canValid=True, gearShifter='drive',
                                               steeringPressed=False, brakePressed=brake, gasPressed=False))


def test_input_fixture_cruise_button_is_not_accelerator_and_brake_disables():
  telemetry, reducer = Telemetry(), Reducer()
  reducer.update(feed_state(telemetry))
  reducer.update(feed_state(telemetry, 1.01, accel_button=True))
  assert totals(reducer)['interventions'] == 0
  reducer.update(feed_state(telemetry, 1.02, enabled=False, brake=True))
  assert totals(reducer)['interventions'] == totals(reducer)['disengagements'] == 1
  assert totals(reducer)['gas'] == 0


def test_missing_delayed_mismatched_provenance_excluded():
  t = Telemetry()
  s = feed_state(t, identity='')
  assert not s.usable
  t.feed('starpilotModelV2', 1_010_000_000, True, NS(modelMonoTime=999_000_000, runtimeIdentity=OWNER))
  assert not t.feed('carState', 1_010_000_000, True, NS(vEgo=10, canValid=True, gearShifter='drive',
                    steeringPressed=False, brakePressed=False, gasPressed=False)).usable
  assert feed_state(t, 1.02).usable
  # Missing fresh carControl/selfdriveState must not become a disable.
  assert not t.feed('carState', 2_000_000_000, True, NS()).usable


def test_invalid_model_and_future_telemetry_rejected():
  t = Telemetry()
  feed_state(t)
  t.feed('modelV2', 1_010_000_000, False, NS())
  t.feed('starpilotModelV2', 1_010_000_000, True, NS(modelMonoTime=1_010_000_000, runtimeIdentity=OWNER))
  assert not t.feed('carState', 1_020_000_000, True, NS(vEgo=10, canValid=True, gearShifter='drive',
                    steeringPressed=False, brakePressed=False, gasPressed=False)).usable
  t.feed('selfdriveState', 3_000_000_000, True, NS(enabled=False))
  assert not t.feed('carState', 1_030_000_000, True, NS()).usable


class Runner:
  def __init__(self, model, external=False):
    self.stats_identity = loaded_identity(model, external)


def test_loaded_identity_fallback_pairs_restart_and_publication_failure():
  fallback, external, long = Runner('rdf43'), Runner('selected-gpu', True), Runner('long', True)
  assert json.loads(output_identity(fallback))['roles'][0]['modelId'] == 'rdf43'
  assert json.loads(output_identity(external))['roles'][0]['backend'] == 'chestnut'
  assert [r['modelId'] for r in json.loads(output_identity(external, long))['roles']] == ['selected-gpu', 'long']
  assert output_identity(Runner('rdf43')) != output_identity(fallback)
  target = NS(starpilotModelV2=NS())
  publish_identity(target, NS(logMonoTime=123, valid=True), fallback)
  assert target.valid
  assert target.starpilotModelV2.modelMonoTime == 123
  assert json.loads(target.starpilotModelV2.runtimeIdentity)['roles'][0]['modelId'] == 'rdf43'
  publish_identity(object(), object(), fallback)  # old schema/instrumentation failure cannot raise


def test_integration_is_optional_and_publication_only():
  root = Path(__file__).resolve().parents[3]
  manager = (root / 'system/manager/process_config.py').read_text()
  controls = (root / 'selfdrive/selfdrived/selfdrived.py').read_text()
  assert 'model_statsd' not in manager and 'model_statsd' not in controls
  source = (root / 'selfdrive/modeld/modeld.py').read_text()
  assert source.index("pm.send('modelV2', modelv2_send)") < source.index('publish_identity(starpilot_modelv2_send')
  observer = (root / 'starpilot/system/model_statsd.py').read_text()
  assert 'PubMaster(' not in observer and 'Params(' not in observer
  assert 'conflate=False' in observer
