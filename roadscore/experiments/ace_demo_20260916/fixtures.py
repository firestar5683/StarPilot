"""Recorded cases plus clearly labeled synthetic false-positive controls; no route input."""
import os
import sys,json
from pathlib import Path
import numpy as np,soundfile as sf
R=Path(__file__).resolve().parents[2];OLD=R/'results/ace_stability_20260916';OUT=R/'results/ace_demo_20260916';sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from quality_gate import inspect
fixtures=[('bad_chorus','live_community_chorus/native_committed/audio.wav',8,'chorus',False),('bad_curve_verse','live_curve_verse/native_committed/audio.wav',8,'verse',False),('old_terminal_verse','legacy_verse/native_0/audio.wav',0,'verse',False),('normal_verse','prism_30/native_0/audio.wav',0,'initial',True),('prechorus','window45_prechorus/native_adaptive_00/audio.wav',8,'prechorus',True),('conservative_bridge','window45_bridge/native_adaptive_02/audio.wav',8,'bridge',True),('intentional_outro','window45_outro/native_adaptive_03/audio.wav',8,'outro',True)]
rows=[]
for name,path,prefix,role,expected in fixtures:
 f=OLD/'cases'/path
 if not f.exists():raise FileNotFoundError(f)
 a,s=sf.read(f,dtype='float32',always_2d=True)
 if (f.parent/'endpoint.json').exists():a=a[:round(json.loads((f.parent/'endpoint.json').read_text())['committed_seconds']*s)]
 q=inspect(a/.65,s,prefix,role=role);rows.append({'name':name,'file':str(f.relative_to(R)),'kind':'recorded native model output','expected_accept':expected,'matches_expected':q['accepted']==expected,'quality':q})
base,s=sf.read(OLD/'cases/prism_30/native_0/audio.wav',dtype='float32',always_2d=True);base/= .65
for name,a in [('soft_intro',base*.035),('sparse_section',base*.07),('short_breakdown',base.copy())]:
 if name=='short_breakdown':a[10*s:round(11.2*s)]=0
 q=inspect(a,s,0,role='initial' if name=='soft_intro' else 'verse');rows.append({'name':name,'kind':'controlled amplitude/rest transform of a generated clip; not a separately human-approved performance','expected_accept':True,'matches_expected':q['accepted'],'quality':q})
# Post-run regression: a raw-scale pass became a two-second quiet interval after DSP.
scale_case=R/'routes'/os.environ['ROADSCORE_CURVE_ROUTE']/'roadscore/normal_1789613226/quality/1789613240559/attempt_0.wav'
if scale_case.exists():
 a,s=sf.read(scale_case,dtype='float32',always_2d=True);q=inspect(a/.65,s,8,role='verse');rows.append({'name':'output_scale_quiet_interval','file':str(scale_case.relative_to(R)),'kind':'recorded native output, post-run final-PCM regression','expected_accept':False,'matches_expected':not q['accepted'],'quality':q})
(OUT/'quality_fixtures.json').write_text(json.dumps(rows,indent=2))
for r in rows:print(r['name'],r['quality']['accepted'],r['quality']['longest_quiet_seconds'],r['quality']['reasons'])
assert all(x['matches_expected'] for x in rows),'Fixture mismatch; investigate before changing thresholds.'
