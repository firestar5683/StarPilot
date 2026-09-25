"""One isolated FLM operation never publishes a partial or unparked report."""

from pathlib import Path
import json
import subprocess
import sys
import threading
import time
from unittest import mock

import pytest
import zstandard as zstd

from openpilot.cereal import messaging
from openpilot.starpilot.flm.operation_owner import FlmAnalysisOwner, FlmOperationError


SEGMENT = '1234abcd--0123456789--0'


def recording(tmp_path: Path, *, valid: bool = True) -> Path:
  root = tmp_path.resolve()
  folder = root / SEGMENT
  folder.mkdir()
  event = messaging.new_message('deviceState', valid=True)
  event.logMonoTime = 1234
  (folder / 'rlog.zst').write_bytes(zstd.ZstdCompressor().compress(event.to_bytes()) if valid else b'bad zstd')
  return root


def terminal(owner: FlmAnalysisOwner) -> dict:
  deadline = time.monotonic() + 5
  while time.monotonic() < deadline:
    state = owner.snapshot()
    if state['state'] != 'running':
      return state
    time.sleep(0.01)
  raise AssertionError('operation did not terminate')


def test_real_local_worker_report_source_identity_and_stale_id(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  try:
    started = owner.start((SEGMENT,))
    assert started['operationId'].count(':') == 1 and started['selected'] == 1
    assert terminal(owner)['state'] == 'completed'
    report = owner.report(started['operationId'])
    assert report['schemaVersion'] == 1 and report['vehicleQualification'] is False
    assert report['segments'][0]['source']['segmentName'] == SEGMENT
    assert report['segments'][0]['analysis']['status'] == 'missing_car_params'
    report['segments'].clear()
    assert len(owner.report(started['operationId'])['segments']) == 1
    next_run = owner.start((SEGMENT,))
    with pytest.raises(FlmOperationError, match='operation_changed'):
      owner.report(started['operationId'])
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(next_run['operationId'])['operationId'] == next_run['operationId']
  finally:
    owner.close()


def test_request_thread_can_exit_while_monitor_owned_child_completes(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  replies = []
  request_thread = threading.Thread(target=lambda: replies.append(owner.start((SEGMENT,))))
  try:
    request_thread.start()
    request_thread.join(timeout=2)
    assert not request_thread.is_alive() and len(replies) == 1
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(replies[0]['operationId'])['segments'][0]['analysis']['status'] == 'missing_car_params'
  finally:
    owner.close()


def test_failed_monitor_start_is_unavailable_and_does_not_wedge_future_analysis(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  try:
    with mock.patch.object(threading.Thread, 'start', side_effect=RuntimeError('thread unavailable')):
      with pytest.raises(FlmOperationError, match='unavailable'):
        owner.start((SEGMENT,))
    assert owner.snapshot()['state'] == 'failed'
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(token)['operationId'] == token
  finally:
    owner.close()


def test_corrupt_and_symlinked_local_sources_publish_no_report(tmp_path):
  root = recording(tmp_path, valid=False)
  owner = FlmAnalysisOwner(root=root, parked=lambda: True)
  try:
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
    path = root / SEGMENT / 'rlog.zst'
    path.unlink()
    path.symlink_to(root / 'outside')
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
  finally:
    owner.close()


def test_cancel_busy_and_onroad_kill_isolated_slow_child(tmp_path):
  root = recording(tmp_path)
  parked = [True]
  slow_worker = (sys.executable, '-c', 'import sys,time;sys.stdin.buffer.read();time.sleep(30)')
  owner = FlmAnalysisOwner(root=root, parked=lambda: parked[0], worker_argv=slow_worker)
  try:
    token = owner.start((SEGMENT,))['operationId']
    with pytest.raises(FlmOperationError, match='busy'):
      owner.start((SEGMENT,))
    assert owner.cancel(token)['state'] == 'canceled'
    token = owner.start((SEGMENT,))['operationId']
    with owner._lock:
      parked[0] = False
      assert owner.snapshot()['state'] == 'unavailable'
      parked[0] = True
      with pytest.raises(FlmOperationError, match='busy'):
        owner.start((SEGMENT,))
    parked[0] = False
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
  finally:
    owner.close()


def test_worker_pipe_eof_while_alive_and_selector_failure_reap(tmp_path):
  root = recording(tmp_path)
  eof_worker = (sys.executable, '-c', 'import os,sys,time;sys.stdin.buffer.read();os.close(1);time.sleep(30)')
  owner = FlmAnalysisOwner(root=root, parked=lambda: True, worker_argv=eof_worker)
  try:
    owner.start((SEGMENT,))
    assert terminal(owner)['state'] == 'failed'
    assert owner._child is None
  finally:
    owner.close()

  class BrokenSelector:
    def __enter__(self):
      return self
    def __exit__(self, *args):
      return False
    def register(self, *_args):
      raise OSError('injected selector failure')

  with mock.patch('openpilot.starpilot.flm.operation_owner.selectors.DefaultSelector', BrokenSelector):
    owner = FlmAnalysisOwner(root=root, parked=lambda: True, worker_argv=eof_worker)
    try:
      owner.start((SEGMENT,))
      assert terminal(owner)['state'] == 'failed'
      assert owner._child is None
    finally:
      owner.close()


def test_close_stops_child_and_revokes_report(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  token = owner.start((SEGMENT,))['operationId']
  assert terminal(owner)['state'] == 'completed'
  owner.close()
  with pytest.raises(FlmOperationError, match='unavailable'):
    owner.report(token)


def test_worker_rejects_stale_parent_identity_before_any_log_read(tmp_path):
  root = recording(tmp_path)
  child = subprocess.run((sys.executable, '-m', 'openpilot.starpilot.flm.operation_worker'),
                         input=json.dumps({'root': str(root), 'segments': [SEGMENT], 'parentPid': 1}).encode(),
                         capture_output=True, timeout=5, check=False)
  assert child.returncode != 0
  assert b'"kind":"result"' not in child.stdout
  assert b'"code":"process_failed"' in child.stdout


def test_wall_deadline_stops_and_reaps_child(tmp_path):
  worker = (sys.executable, '-c', 'import sys,time;sys.stdin.buffer.read();time.sleep(30)')
  with mock.patch('openpilot.starpilot.flm.operation_owner.WALL_DEADLINE_SECONDS', 0.05):
    owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True, worker_argv=worker)
    try:
      owner.start((SEGMENT,))
      status = terminal(owner)
      assert status['state'] == 'failed' and status['errorCode'] == 'deadline'
      assert owner._child is None
    finally:
      owner.close()


def test_invalid_selection_and_unparked_start_do_not_spawn(tmp_path):
  owner = FlmAnalysisOwner(root=tmp_path.resolve(), parked=lambda: False)
  try:
    for names in ((), (SEGMENT, SEGMENT), ('../outside',)):
      with pytest.raises(FlmOperationError, match='invalid_request'):
        owner.start(names)
    with pytest.raises(FlmOperationError, match='not_parked'):
      owner.start((SEGMENT,))
    assert owner.snapshot()['state'] == 'idle'
  finally:
    owner.close()


def test_gm_live_trial_atomic_restore_preserves_other_choices_and_rejects_changed_source():
  from dataclasses import replace
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
  from openpilot.starpilot.flm.live import GmLiveSource, gm_capability
  from openpilot.starpilot.flm.torque_surface import GmSurface
  from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
  from openpilot.starpilot.lateral.torque_settings import (DOCUMENT_KEY, FieldChoice, parse_document, replace_field,
                                                         replace_geometry, serialize_document)
  cp = ordinary_params(CAR.CHEVROLET_MALIBU_ASCM).as_reader()
  with OpenpilotPrefix():
    saved = Params()
    mode = ControllerMode.STARPILOT
    saved.put('LateralControllerSelection', json.loads(replace_mode(None, cp, mode)), block=True)
    cap = gm_capability(cp, mode)
    identity = cap['fingerprint']
    profiles = replace_field({}, identity, cap['basis'], 'friction', 'custom', cap['basis'][2] * 1.1)
    profiles = replace_geometry(profiles, identity, cap['basis'], (cp.steerRatio, cp.steerActuatorDelay+.2),
                                'ratio', FieldChoice('custom', cp.steerRatio * 1.1))
    saved.put(DOCUMENT_KEY, json.loads(serialize_document(profiles)), block=True)
    context = SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True)
    owner = FlmTrialOwner(saved, SimpleNamespace(sample=lambda: context))

    def action(operation, **fields):
      return owner.action({'action': operation, 'token': owner.snapshot()['token'], **fields})

    for key, gain in (('baseline', .1), ('trial', .3)):
      action('save', id=key, label=key, surface=GmSurface(cap['profile'], {'ff_gain_left': gain}).document())
    first = action('apply', id='baseline')
    action('accept', trial=first['state']['trial'])
    trial = action('trial', id='trial')
    token = trial['state']['trial']
    self_profile = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())[identity]
    assert self_profile.flm.active == 'trial' and self_profile.flm.baseline_active == 'baseline'
    source = GmLiveSource(cp, mode, saved)
    assert source.sample(active=True, speed=20., now_ns=1_000_000_000).knobs['ff_gain_left'] == .3
    before = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    with pytest.raises(FlmOperationError, match='busy'):
      action('save', id='baseline', label='changed', surface=GmSurface(cap['profile'], {}).document())
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == before
    restored = action('restore', trial=token)
    assert restored['state']['active'] == 'baseline'
    trial = action('trial', id='trial')
    token = trial['state']['trial']
    before = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    # A concurrent explicit manual edit rejects even refreshed restore. Accept
    # keeps that user edit and clears the old baseline without overwriting it.
    latest = parse_document(before)
    latest = replace_field(latest, identity, cap['basis'], 'friction', 'custom', cap['basis'][2] * 1.2)
    saved.put(DOCUMENT_KEY, json.loads(serialize_document(latest)), block=True)
    with pytest.raises(FlmOperationError, match='operation_changed'):
      owner.action({'action': 'restore', 'token': trial['token'], 'trial': token})
    with pytest.raises(FlmOperationError, match='operation_changed'):
      action('restore', trial=token)
    assert owner.snapshot()['manualConflict']
    restored = action('accept', trial=token)
    after = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert after[identity].friction == latest[identity].friction
    assert after[identity].geometry == profiles[identity].geometry
    assert after[identity].flm.active == 'trial' and after[identity].flm.trial is None
    assert restored['state']['applied']
    assert source.sample(active=True, speed=20., now_ns=2_000_000_000).knobs['ff_gain_left'] == .3
    action('disable')
    assert source.sample(active=True, speed=20., now_ns=3_000_000_000) is None
    assert len(parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())[identity].flm.saved) == 2
    frozen = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    valid = iter((True, False))
    with pytest.raises(FlmOperationError, match='operation_changed'):
      owner.action({'action': 'trial', 'token': owner.snapshot()['token'], 'id': 'trial'},
                   session_valid=lambda: next(valid, False))
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == frozen, 'authority is rechecked before atomic write'
    context.parked = False
    with pytest.raises(FlmOperationError, match='not_parked'):
      action('trial', id='trial')
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == frozen
    context.parked = True
    bad = cp.as_builder()
    bad.lateralTuning.torque.latAccelFactor *= 1.01
    context.cp, context.cp_raw = bad.as_reader(), bad.to_bytes()
    snapshot = owner.snapshot()
    assert not snapshot['available'] and snapshot['resettable']
    with pytest.raises(FlmOperationError, match='operation_changed'):
      action('trial', id='trial')
    action('reset')
    result = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert result[identity] == replace(after[identity], flm=None), 'changed-basis reset is FLM-only'
    assert not Path(saved.get_param_path('FLMTrialApplied')).exists()


def test_gm_live_exact_controller_vehicle_basis_absence_and_malformed_never_rewrite():
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.live import GmLiveSource, gm_capability
  from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
  from openpilot.starpilot.flm.torque_surface import GmSurface, GmFlmBinding
  from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
  from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, PlatformProfile, FieldChoice, parse_document, serialize_document
  cp = ordinary_params(CAR.CHEVROLET_MALIBU_ASCM).as_reader()
  with OpenpilotPrefix():
    saved = Params()
    saved.put('LateralControllerSelection', json.loads(replace_mode(None, cp, ControllerMode.STARPILOT)), block=True)
    cap = gm_capability(cp, ControllerMode.STARPILOT)
    source = GmLiveSource(cp, ControllerMode.STARPILOT, saved)
    assert source.sample(active=True, speed=20., now_ns=1_000_000_000) is None
    assert not Path(saved.get_param_path(DOCUMENT_KEY)).exists()
    binding = GmFlmBinding('starpilot', cap['policy'], cap['basis'],
                          (('one', 'One', GmSurface(cap['profile'], {'ff_gain_left': .3})),), 'one', True)
    for controller, basis, identity in (('standard', cap['basis'], cap['fingerprint']),
                                        ('starpilot', (cap['basis'][0]*1.01, *cap['basis'][1:]), cap['fingerprint']),
                                        ('starpilot', cap['basis'], str(CAR.CADILLAC_XT4))):
      from dataclasses import replace
      rejected = replace(binding, controller=controller, basis=basis)
      raw = serialize_document({identity: PlatformProfile(cap['basis'], FieldChoice(), FieldChoice(), flm=rejected)})
      saved.put(DOCUMENT_KEY, json.loads(raw), block=True)
      source.last_ns = None
      assert source.sample(active=True, speed=20., now_ns=2_000_000_000) is None
      assert parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()) == parse_document(raw)
    stale_basis = (cap['basis'][0]*1.01, *cap['basis'][1:])
    saved.put(DOCUMENT_KEY, json.loads(serialize_document({cap['fingerprint']: PlatformProfile(stale_basis, FieldChoice(), FieldChoice())})), block=True)
    ctx = SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True)
    stale_owner = FlmTrialOwner(saved, SimpleNamespace(sample=lambda: ctx))
    assert not stale_owner.snapshot()['available'], 'outer manual profile basis is also part of live admission'
    frozen = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    with pytest.raises(FlmOperationError, match='operation_changed'):
      stale_owner.action({'action': 'save', 'token': stale_owner.snapshot()['token'], 'id': 'one', 'label': 'One',
                          'surface': GmSurface(cap['profile'], {}).document()})
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == frozen
    Path(saved.get_param_path(DOCUMENT_KEY)).write_bytes(b'{')
    source.last_ns = None
    assert source.sample(active=True, speed=20., now_ns=3_000_000_000) is None
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == b'{'
    ctx = SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True)
    assert not FlmTrialOwner(saved, SimpleNamespace(sample=lambda: ctx)).snapshot()['available']


def test_gm_bundle_full_manual_switch_restore_guard_precedence_and_other_vehicle_preserved():
  from dataclasses import replace
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_bolt_cc import params as bolt_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
  from openpilot.starpilot.flm.live import gm_capability
  from openpilot.starpilot.flm.manual_trial import manual_snapshot
  from openpilot.starpilot.flm.torque_surface import GmSurface
  from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
  from openpilot.starpilot.lateral.torque_settings import (DOCUMENT_KEY, FieldChoice, GainBasis, GeometryProfile,
                                                         PlatformProfile, parse_document, serialize_document)
  cp = bolt_params(CAR.CHEVROLET_BOLT_CC_2022_2023, alpha=True).as_reader()
  with OpenpilotPrefix():
    saved = Params()
    saved.put('LateralControllerSelection', json.loads(replace_mode(None, cp, ControllerMode.STARPILOT)), block=True)
    saved.put('AdvancedLateralTune', False, block=True)
    saved.put('ForceAutoTuneOff', True, block=True)
    cap = gm_capability(cp, ControllerMode.STARPILOT)
    identity = cap['fingerprint']
    baseline = PlatformProfile(cap['basis'], FieldChoice(), FieldChoice())
    other = str(CAR.CHEVROLET_MALIBU_ASCM)
    profiles = {identity: baseline, other: PlatformProfile((2., 0., .1), FieldChoice('custom', 2.2), FieldChoice())}
    saved.put(DOCUMENT_KEY, json.loads(serialize_document(profiles)), block=True)
    ctx = SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True)
    owner = FlmTrialOwner(saved, SimpleNamespace(sample=lambda: ctx))
    gain = GainBasis('starpilot', ((0,), (.6,)), cap['basis'])
    geometry = GeometryProfile((cp.steerRatio, cp.steerActuatorDelay + .2), FieldChoice('custom', cp.steerRatio * 1.1),
                               FieldChoice('custom', .7), False, 'force_auto')
    one = replace(baseline, factor=FieldChoice('custom', cap['basis'][0] * 1.1),
                  friction=FieldChoice('custom', min(.1, cap['basis'][2]*1.1)),
                  proportional_gain=FieldChoice('custom', .7), gain_basis=gain, geometry=geometry)
    two = replace(baseline, geometry=replace(geometry, ratio=FieldChoice(), full_delay=FieldChoice(),
                                           automatic_delay=True, learning='source'))
    def save(key, profile):
      owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': key, 'label': key,
                    'surface': GmSurface(cap['profile'], {}).document()}, generated_manual=manual_snapshot(profile, identity))
    save('one', one)
    save('two', two)
    reasons = owner.snapshot()['preconditions']['one']
    assert any('Advanced' in reason for reason in reasons) and any('Off remains' in reason for reason in reasons)
    frozen = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    with pytest.raises(FlmOperationError, match='unavailable'):
      owner.action({'action': 'trial', 'token': owner.snapshot()['token'], 'id': 'one'})
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == frozen
    assert saved.get_bool('ForceAutoTuneOff') and not saved.get_bool('AdvancedLateralTune')
    # Only the user explicitly changes prerequisites; FLM never writes them.
    saved.put('ForceAutoTuneOff', False, block=True)
    saved.put('AdvancedLateralTune', True, block=True)
    preferences = {key: saved.get(key) for key in ('ForceAutoTuneOff', 'AdvancedLateralTune', 'LateralControllerSelection')}
    def apply(key):
      return owner.action({'action': 'trial', 'token': owner.snapshot()['token'], 'id': key})
    trial = apply('one')
    current = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert replace(current[identity], flm=None) == one
    switched = apply('two')
    current = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert replace(current[identity], flm=None) == two, 'source choices replace every earlier custom field'
    assert switched['state']['trial'] == trial['state']['trial']
    owner.action({'action': 'restore', 'token': owner.snapshot()['token'], 'trial': trial['state']['trial']})
    current = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert replace(current[identity], flm=None) == baseline
    assert current[other] == profiles[other]
    assert preferences == {key: saved.get(key) for key in preferences}
    from openpilot.starpilot.flm.gm_recommend import build_report, same_numerical_context
    source = owner.training_context(owner.snapshot()['token'])
    evidence = build_report(source, [], {'sampleCount': 32, 'meanErrorAbs': .03})
    before_progress = Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes()
    assert not owner.record_cleanup({'gmEvidence': evidence}, session_valid=lambda: False)
    assert Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes() == before_progress
    assert owner.record_cleanup({'gmEvidence': evidence}, session_valid=lambda: True)
    recorded = parse_document(Path(saved.get_param_path(DOCUMENT_KEY)).read_bytes())
    assert recorded[identity].flm.cleanup_progress and not recorded[identity].flm.applied
    assert replace(recorded[identity], flm=None) == baseline
    assert recorded[other] == profiles[other]
    assert preferences == {key: saved.get(key) for key in preferences}
    fresh = owner.training_context(owner.snapshot()['token'])
    assert fresh['cleanupProgress'] and same_numerical_context(fresh, source)
    assert not same_numerical_context({**fresh, 'geometryBasis': [cp.steerRatio*1.01, cp.steerActuatorDelay+.2]}, source)
    assert build_report(fresh, [], {'sampleCount': 32, 'meanErrorAbs': .03})['decision']['cleanupProgressLocked']



def test_gm_stale_rich_controller_binding_exposes_reset_only_and_preserves_manual():
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_bolt_cc import params as bolt_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
  from openpilot.starpilot.flm.live import gm_capability
  from openpilot.starpilot.flm.torque_surface import GmSurface
  from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
  from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, FieldChoice, PlatformProfile, parse_document, serialize_document
  cp = bolt_params(CAR.CHEVROLET_BOLT_CC_2022_2023, alpha=True).as_reader()
  with OpenpilotPrefix():
    params = Params()
    params.put('LateralControllerSelection', json.loads(replace_mode(None, cp, ControllerMode.STARPILOT)), block=True)
    cap = gm_capability(cp, ControllerMode.STARPILOT)
    profile = PlatformProfile(cap['basis'], FieldChoice('custom', cap['basis'][0]*1.1), FieldChoice())
    params.put(DOCUMENT_KEY, json.loads(serialize_document({cap['fingerprint']: profile})), block=True)
    context = SimpleNamespace(sample=lambda: SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True))
    owner = FlmTrialOwner(params, context)
    owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': 'rich', 'label': 'Rich',
                  'surface': GmSurface(cap['profile'], {}).document()})
    params.put('LateralControllerSelection', json.loads(replace_mode(
      Path(params.get_param_path('LateralControllerSelection')).read_bytes(), cp, ControllerMode.STANDARD)), block=True)
    stale = owner.snapshot()
    assert not stale['available'] and not stale['editable'] and stale['resettable']
    assert stale['profile'] == 'torque_universal' and stale['state']['saved']['rich']['surface']['profile'] == 'gm_bolt_2022_2023'
    owner.action({'action': 'reset', 'token': stale['token']})
    assert owner.snapshot()['available']
    from opendbc.car.lateral import FRICTION_THRESHOLD
    assert owner.snapshot()['curveDefaults'] == [FRICTION_THRESHOLD] * 5
    assert parse_document(Path(params.get_param_path(DOCUMENT_KEY)).read_bytes())[cap['fingerprint']] == profile



def test_real_gm_worker_frozen_source_report_cannot_grant_or_mutate_preferences(tmp_path):
  from openpilot.cereal import log
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.gm_recommend import source_context
  from openpilot.starpilot.lateral.torque_settings import PlatformProfile, FieldChoice
  from openpilot.starpilot.flm.tests.test_offline import event
  cp = ordinary_params(CAR.CHEVROLET_MALIBU_ASCM).as_reader()
  tune = cp.lateralTuning.torque
  with OpenpilotPrefix():
    params = Params()
    context = source_context(cp, 'starpilot', params, 'a'*64,
                             PlatformProfile((tune.latAccelFactor, tune.latAccelOffset, tune.friction), FieldChoice(), FieldChoice()))
    folder = tmp_path/SEGMENT
    folder.mkdir()
    cp_event = log.Event.new_message(logMonoTime=1_000_000_000, valid=True)
    cp_event.init('carParams').from_dict(cp.to_dict())
    rows = [cp_event]
    for index in range(250):
      ns = 1_000_000_000 + (index+1)*20_000_000
      state = event('carState', ns)
      state.carState.steeringAngleDeg = 3.
      controls = event('controlsState', ns, desired=.8, actual=.1)
      controls.controlsState.lateralControlState.torqueState.output = .2
      rows.extend((state, event('carControl', ns), controls))
    raw = b''.join(row.to_bytes() for row in rows)
    (folder/'rlog.zst').write_bytes(zstd.ZstdCompressor().compress(raw))
    owner = FlmAnalysisOwner(root=tmp_path, parked=lambda: True)
    before = {key: params.get(key) for key in ('TorqueOverrideDocument', 'LateralControllerSelection', 'ForceAutoTuneOff', 'AdvancedLateralTune')}
    try:
      started = owner.start((SEGMENT,), gm_context=context)
      assert terminal(owner)['state'] == 'completed'
      report = owner.report(started['operationId'])
      assert report['purpose'] == 'gm_flm_evidence_profiles'
      assert report['gmEvidence']['context'] == context
      assert report['gmEvidence']['stats']['sampleCount'] > 0
      assert report['gmEvidence']['fit'] is False and report['vehicleQualification'] is False
      assert report['tuneRecommendation'] is None, 'original symptom trials never become an autonomous tuning grant'
      assert report['segments'][0]['source']['sha256'] == __import__('hashlib').sha256((folder/'rlog.zst').read_bytes()).hexdigest()
      assert before == {key: params.get(key) for key in before}, 'isolated worker has no Params writer'
    finally:
      owner.close()


def test_gm_bundle_preserves_inactive_finite_choices_but_rejects_consumed_bounds():
  from dataclasses import replace
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.live import gm_capability
  from openpilot.starpilot.flm.manual_trial import manual_profile, manual_snapshot
  from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
  from openpilot.starpilot.flm.torque_surface import GmSurface
  from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
  from openpilot.starpilot.lateral.torque_settings import (DOCUMENT_KEY, MAX_DOCUMENT_BYTES, FieldChoice, GainBasis,
                                                         PlatformProfile, parse_document, serialize_document)
  cp = ordinary_params(CAR.CHEVROLET_MALIBU_ASCM).as_reader()
  with OpenpilotPrefix():
    params = Params()
    params.put('LateralControllerSelection', json.loads(replace_mode(None, cp, ControllerMode.STARPILOT)), block=True)
    cap = gm_capability(cp, ControllerMode.STARPILOT)
    identity = cap['fingerprint']
    # Source selections retain previously entered finite numbers, even when
    # those inactive numbers are outside the current consumption bounds.
    baseline = PlatformProfile(cap['basis'], FieldChoice('source', 10000.), FieldChoice('source', 10000.),
                               FieldChoice('source', 10000.), GainBasis('starpilot', ((0,), (.6,)), cap['basis']))
    raw = serialize_document({identity: baseline})
    params.put(DOCUMENT_KEY, json.loads(raw), block=True)
    owner = FlmTrialOwner(params, SimpleNamespace(sample=lambda: SimpleNamespace(cp=cp, cp_raw=cp.as_builder().to_bytes(), parked=True)))
    snapshot = manual_snapshot(baseline, identity)
    assert manual_profile(snapshot, identity, cap['basis']) == baseline
    assert len(snapshot.encode()) < 4096 and MAX_DOCUMENT_BYTES == 16384
    owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': 'latent', 'label': 'Latent',
                  'surface': GmSurface(cap['profile'], {}).document()})
    frozen = Path(params.get_param_path(DOCUMENT_KEY)).read_bytes()
    for name in ('factor', 'friction', 'proportional_gain'):
      invalid = replace(baseline, **{name: FieldChoice('custom', 10000.)})
      with pytest.raises(ValueError):
        owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': 'invalid', 'label': 'Invalid',
                      'surface': GmSurface(cap['profile'], {}).document()},
                     generated_manual=manual_snapshot(invalid, identity))
      assert Path(params.get_param_path(DOCUMENT_KEY)).read_bytes() == frozen
    # An ordinary Save also validates the currently captured consumed fields,
    # rather than depending on a later full-document parse to reject them.
    params.put(DOCUMENT_KEY, json.loads(serialize_document({identity: replace(baseline, factor=FieldChoice('custom', 10000.))})), block=True)
    invalid_raw = Path(params.get_param_path(DOCUMENT_KEY)).read_bytes()
    with pytest.raises(ValueError):
      owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': 'invalid', 'label': 'Invalid',
                    'surface': GmSurface(cap['profile'], {}).document()})
    assert Path(params.get_param_path(DOCUMENT_KEY)).read_bytes() == invalid_raw
    params.put(DOCUMENT_KEY, json.loads(frozen), block=True)
    changed = replace(baseline, factor=FieldChoice('custom', cap['basis'][0]*1.05))
    owner.action({'action': 'save', 'token': owner.snapshot()['token'], 'id': 'custom', 'label': 'Custom',
                  'surface': GmSurface(cap['profile'], {}).document()}, generated_manual=manual_snapshot(changed, identity))
    trial = owner.action({'action': 'trial', 'token': owner.snapshot()['token'], 'id': 'custom'})
    owner.action({'action': 'trial', 'token': owner.snapshot()['token'], 'id': 'latent'})
    assert replace(parse_document(Path(params.get_param_path(DOCUMENT_KEY)).read_bytes())[identity], flm=None) == baseline
    owner.action({'action': 'restore', 'token': owner.snapshot()['token'], 'trial': trial['state']['trial']})
    restored = parse_document(Path(params.get_param_path(DOCUMENT_KEY)).read_bytes())[identity]
    assert replace(restored, flm=None) == baseline
    assert len(Path(params.get_param_path(DOCUMENT_KEY)).read_bytes()) <= MAX_DOCUMENT_BYTES
