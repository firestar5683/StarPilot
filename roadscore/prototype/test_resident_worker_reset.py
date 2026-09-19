"""Exercise the worker's real reset function without importing or initializing a GPU."""
import ast
import os
from pathlib import Path
import resource
import time
from types import SimpleNamespace
import numpy as np
import pytest
from generation_seed import sample_seed
from resident_session import validate_session

BANK = 'a' * 64

class Plan:
    def __init__(self, bank, root, seed, profile):
        self.bank_hash = BANK
        self.index = 0
    def begin(self, previous):
        assert previous is None and self.index == 0
        return 'initial'
    def accept(self, wave, latent):
        self.index += 1

class Generator:
    def __init__(self, generate, policy):
        self.policy = policy
    def run(self, role, seed, previous, record):
        assert previous is None
        rng = np.random.default_rng(seed)
        return rng.standard_normal((480, 2)), rng.standard_normal((1, 4, 64)), {'prefix_seconds': 0}

@pytest.fixture
def worker(tmp_path, monkeypatch):
    path=Path(__file__).resolve().parents[1]/'experiments/ace_chestnut_20260916/ace_worker.py'
    function=next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name=='prepare_session')
    code=compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(path),'exec')
    saved={};audio=[];model=object();policy=SimpleNamespace(initial_buffer_seconds=.01,output_gain=.65)
    monkeypatch.setenv('ROADSCORE_PLAN_BANK',str(tmp_path/'bank'))
    state=dict(profile='prism',base_seed=123,preparation_id='cold',planned=Plan(None,None,123,'prism'),
               qualified=Generator(None,policy),composition_policy='hook-cache-v1',validate_session=validate_session,
               G=tmp_path,Path=Path,os=os,time=time,np=np,resource=resource,BOOT=time.monotonic(),
               ready=tmp_path/'worker_ready',CachedComposition=Plan,QualifiedGenerator=Generator,
               generate=None,HOOK_POLICY=policy,POLICY=policy,windowed=True,resident=True,c=model,
               model_load_seconds=12.,record_for=lambda job:None,sample_seed=sample_seed,
               write_json=lambda path,value:saved.update({path.name:value}),
               save_wave=lambda path,wave:audio.append(wave.copy()))
    exec(code,state)
    return state,saved,audio,model

def selection(seed=123,bank=BANK):
    return dict(profile='prism',generation_seed=seed,composition_policy='hook-cache-v1',bank_sha256=bank)

def test_cold_then_warm_same_seed_equal_and_new_seed_varies(worker):
    state,saved,audio,model=worker
    state['prepare_session']()
    old_plan=state['planned'];old_gate=state['qualified']
    state['prepare_session'](selection())
    np.testing.assert_array_equal(audio[0],audio[1])
    assert state['planned'] is not old_plan and state['qualified'] is not old_gate
    assert state['c'] is model
    assert saved['ace_initial.json']['resident_reused'] is True
    assert saved['ace_initial.json']['model_load_seconds']==0
    state['prepare_session'](selection(124))
    assert not np.array_equal(audio[0],audio[2])
    assert saved['ace_initial.json']['generation_seed']==124

def test_pending_continuation_cannot_be_erased_by_reset(worker):
    state,saved,audio,model=worker
    state['prepare_session']()
    request=state['G']/'request.json';request.write_text('preserve')
    old=state['planned']
    with pytest.raises(RuntimeError,match='Pending continuation'):state['prepare_session'](selection(124))
    assert request.read_text()=='preserve' and state['planned'] is old

def test_wrong_bank_does_not_change_existing_session(worker):
    state,saved,audio,model=worker
    with pytest.raises(ValueError,match='identity changed'):state['prepare_session'](selection(124,'b'*64))
    assert state['base_seed']==123 and audio==[]


def test_nonresident_launch_cannot_reuse_resident_audio_with_same_seed():
    from prepared_session import verify
    metadata={'generation_seed':123,'prepared_profile':'prism','composition_policy':'hook-cache-v1','resident_capable':True}
    env={'ROADSCORE_GENERATION_SEED':'123','ROADSCORE_ACE_PROFILE':'prism','ROADSCORE_COMPOSITION_POLICY':'hook-cache-v1'}
    with pytest.raises(ValueError,match='opted-in'):verify(metadata,env)
