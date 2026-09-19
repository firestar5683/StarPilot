"""Focused private listening review; all controls are manual, never autoplay."""
from pathlib import Path
import json,html,os
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
def player(path,label):
 p=R/path
 if not p.exists():return '<p class="pending">'+html.escape(label)+': pending current-pass evidence.</p>'
 return '<figure><figcaption>'+html.escape(label)+'</figcaption><audio controls preload="none" src="'+html.escape(os.path.relpath(p,O),quote=True)+'"></audio></figure>'
sections=[]
def add(title,body):sections.append('<section><h2>'+title+'</h2>'+body+'</section>')
add('A · Prism core',player('results/ace_demo_20260916/core_review.wav','Fresh native Prism core from this pass; consistent runtime output level.'))
add('B · Known bad sample',player('results/ace_demo_20260916/bad_community_review.wav','Community chorus: original 5.8-second gap; both rerolls also failed.')+player('results/ace_demo_20260916/bad_curve_review.wav','Curve verse: original 2.7-second gap; compare its accepted reroll below.'))
rerolls=''
for case in ['community','curve']:
 p=O/('bad_'+case)/'result.json'
 if p.exists():
  m=json.loads(p.read_text());rerolls+='<p>'+case+': '+('accepted seed '+str(m['accepted_seed']) if m['quality_accepted'] else 'all permitted attempts rejected; no accepted reroll claimed')+'.</p>'
  if m['quality_accepted']:rerolls+=player('results/ace_demo_20260916/'+case+'_reroll_review.wav',case+': accepted same-role reroll; see gate metrics above.')
add('C · Bounded rerolls',rerolls or '<p class="pending">Trained-weight benchmark pending.</p>')
add('D · Section flow',player('results/ace_demo_20260916/resident_flow/section_flow.wav','Focused real-worker verse → build → chorus → verse → bridge → chorus → outro; runtime gain.'))
bridge=player('results/ace_stability_20260916/cases/window45_bridge/native_adaptive_02/audio.wav','Existing conservative native bridge retained as default.')
for name in ['glass','percussion','air']:bridge+=player('results/ace_stability_20260916/cases/demo45_bridge_'+name+'/demo_reference/committed.wav','New '+name+' arrangement variant · official Mac reference, same source and seed · subjective choice pending.')
add('E · Conservative bridge',bridge)
add('F · Curve Apex V4',player('results/ace_demo_20260916/gestures/dry.wav','Dry source · controlled event fixture')+player('results/ace_demo_20260916/gestures/v4.wav','V4 · predicted curve payoff near 26s; V3 turn motifs retained. No recorded route timing used.'))
rows=json.loads((O/'replay_results.json').read_text()) if (O/'replay_results.json').exists() else []
prism=next((x for x in rows if x.get('full_route_pass') and x['label']=='curve'),None) or next((x for x in rows if x.get('full_route_pass') and not x['label'].startswith('aurora')),None)
add('G · Full Prism route',player(prism['audio'],'Current-pass full normal replay archive · '+prism['label']) if prism else '<p class="pending">Awaiting full current-pass route validation.</p>')
aurora=next((x for x in rows if x.get('full_route_pass') and x['label'].startswith('aurora')),None)
add('H · Aurora backup',player(aurora['audio'],'Current-pass Aurora route archive') if aurora else '<p class="pending">Selectable backup; current-pass full-route validation pending.</p>')
add('I · Reference classification','<p>The established silence cases reproduced on the official Mac reference in the previous pass. They are treated as sampled music failures, not evidence of a Chestnut timing offset. The new native/reference rerolls agree in accept/reject classification. Hardware hangs are tracked separately in the link investigation; waveform-energy acceptance is not a human listening verdict.</p>')
(O/'index.html').write_text('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Prism · demo hardening review</title><style>body{background:#11131d;color:#ecedf6;font:17px/1.55 system-ui;max-width:960px;margin:40px auto;padding:0 24px}h1{font-size:38px}section{background:#1b2030;border:1px solid #343d57;border-radius:14px;padding:18px 24px;margin:22px 0}h2{color:#b6c5ff}audio{width:100%;margin-top:10px}.pending{color:#ebcb8b}figure{margin:22px 0}a{color:#b6c5ff}</style><h1>Prism · demo hardening</h1><p><strong>Prism: primary · Aurora: backup · Circuit: archived</strong></p><p><a href="../../ACE_DEMO_HARDENING.md">Current evidence and limitations</a> · <a href="DEMO_CHECKLIST.md">Launch and recovery</a></p><p>Private listening review. No autoplay. Human listening is deferred while the session is physically muted. Pending items are not represented as passes.</p>'''+''.join(sections))
