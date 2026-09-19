"""Private file-only port review; no autoplay, network assets, or route publication."""
import html,json,os
from pathlib import Path
from bundle import OUT,R
O=OUT
parts=['''<!doctype html><meta charset="utf-8"><title>RoadScore · ACE port quality</title><meta name="viewport" content="width=device-width"><style>body{font:16px system-ui;background:#10151d;color:#eef3fa;max-width:1050px;margin:32px auto;padding:20px;line-height:1.5}h1{font-size:34px}h2{margin-top:36px;border-top:1px solid #394454;padding-top:20px}p{color:#bbc9d9}audio{width:100%;max-width:460px}.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px}.clip{background:#1b2431;padding:14px;border-radius:10px}a{color:#9bd5ff}.notice{border-left:4px solid #e3b859;padding:12px;background:#24251e}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:9px;border-bottom:1px solid #394454}small{color:#aabbd0}</style><h1>ACE · Port quality</h1><p>Private Mac ↔ Chestnut comparisons. No autoplay. All creation and validation remained physically muted; listening judgments are yours.</p><div class="notice">This validation pass is complete; overall acceptance remains blocked by interior silence and intermittent GPU/link failures. Three56s decode failures are preserved, including two VAE-only probes. The latest captured an unhealthy link state before decoder teardown. The fixed-window continuation and route gates below are not automatically promoted by one successful clip.</div>''']
def text(s):parts.append('<p>'+html.escape(s)+'</p>')
def heading(s):parts.append('<h2>'+html.escape(s)+'</h2>')
def audio(label,path):
 path=Path(path);parts.append('<div class="clip"><b>'+html.escape(label)+'</b>')
 if path.exists():parts.append('<audio controls preload="none" src="'+html.escape(os.path.relpath(path,O),quote=True)+'"></audio>')
 else:parts.append('<p>Pending — no completed artifact yet.</p>')
 parts.append('</div>')
def pair(items):
 parts.append('<div class="pair">')
 for label,path in items:audio(label,path)
 parts.append('</div>')
heading('A–C · Three new identities')
for name,desc in [('prism','128 BPM · D minor · crystal plucks'),('aurora','116 BPM · A minor · warm analog and bells'),('circuit','136 BPM · E minor · funk guitar and clavinet')]:
 text(name.title()+' — '+desc+'. Full30s. Identical boundary values; official FP32 reference versus native FP16. Each pair receives only the same constant gain to avoid browser clipping.')
 pair([('Mac official reference',O/f'listening/{name}_30_mac.wav'),('Chestnut native',O/f'listening/{name}_30_native.wav')])
heading('D · Duration behavior')
text('Same Prism identity family, independently prepared duration-specific inputs.30s ≈15.9s;45s ≈23.0s;60s ≈79.9s. These are full output durations, before any continuation guard is discarded.')
pair([(f'Chestnut · {n}s',O/f'listening/prism_{n}_native.wav') for n in [30,45,60]])
text('Inspect the Prism45s region around36s and Circuit30s around13.5s: these have the largest localized latent differences in their comparisons. The page does not label those differences inaudible.')
heading('E · Repeatability and numerical boundaries')
text('Five identical Prism30 runs produced identical latent and PCM hashes. RTF0.5295–0.5320. The broader identity set has progressively accumulating FP16 differences; exact numerical and step evidence is retained.')
parts.append('<p><a href="comparisons.json">Per-step comparisons</a> · <a href="vae_comparisons.json">VAE results</a> · <a href="hang_56.json">Original 56s failure</a> · <a href="decode56_failure.json">First isolated decoder failure</a> · <a href="decode56_failure_time_summary.json">Failure-time link capture</a> · <a href="shape_audit.json">Duration sweep</a> · <a href="precision_audit.json">Precision diagnostics</a></p>')
heading('F · Approved transition and recoverable reconstruction')
audio('Original human-approved Mac verse → chorus',R/'results/composition_20260916/ace/verse_to_chorus.wav')
text('Exact recreation is blocked by missing original random reference-crop/VAE state. The original200 planner codes were recovered. These new paired runs preserve their actual conditioning/noise; they are not falsely labeled the identical old performance.')
pair([('Mac · recovered original planner codes',O/'listening/gold_recovered_codes_mac.wav'),('Chestnut · recovered original planner codes',O/'listening/gold_recovered_codes_native.wav')])
text('Completed matched pair using the original settings, but a newly sampled planner/reference preparation:')
pair([('Mac · newly captured boundary',O/'listening/gold_transition_mac.wav'),('Chestnut · that same boundary',O/'listening/gold_transition_native.wav')])
heading('G · Section flow repair')
text('Fixed lookahead:45s model window,8s preserved prefix, retain through36s unless terminal energy requires an earlier endpoint. The model ending is excluded before selecting the next active source tail. This first140s sequence is verse → prechorus → chorus → bridge → outro, linked by actual generated latents. No gaps were filled with replacement audio. One1.7s quiet passage inside the outro remains in both versions; listen rather than treating energy checks as musical approval.')
pair([('Mac · linked flow',O/'reference_adaptive_plan_flow.wav'),('Chestnut · linked flow',O/'native_adaptive_plan_flow.wav')])
parts.append('<p><a href="reference_adaptive_plan_audit.json">Mac20-step audit</a> · <a href="native_adaptive_plan_audit.json">Chestnut20-step audit</a></p>')
text('Full-route testing later exposed an additional5.1s chorus gap and a2.7s curve-run gap. The chorus gap is reproduced by the official Mac reference from identical inputs; four new seeds also failed. The endpoint guard is therefore a terminal-fade repair, not a general no-silence guarantee. This gate remains open.')
pair([('Live gap · official Mac exact inputs',O/'cases/live_community_chorus/reference_rounded/audio.wav'),('Live gap · actual Chestnut output',O/'cases/live_community_chorus/native_committed/audio.wav')])
parts.append('<details><summary>Additional prepared native identity flows</summary>')
text('Aurora and Circuit each completed six linked native jobs with no hang and no multi-second quiet region. These140s previews include initial/verse/prechorus/chorus/bridge; the separate outro artifacts are retained in each case. Human approval and full-route tests for these identities remain pending.')
pair([('Aurora · Chestnut linked preview',O/'aurora_native_profile_plan_flow.wav'),('Circuit · Chestnut linked preview',O/'circuit_native_profile_plan_flow.wav')])
parts.append('</details>')
heading('H · Decoder isolation')
text('Exactly the same45s native latent tensor. Official Mac FP32 full decode versus Chestnut FP16 bounded decode. Every measured one-second window had zero sample lag; relative waveform error≈0.073%.')
pair([('Mac VAE',O/'cases/prism_45/same_latent_vae/mac.wav'),('Chestnut VAE',O/'cases/prism_45/native_0/audio.wav')])
heading('I · Gesture V3')
text('Synthetic event fixture, not route-specific timestamps. Turn signal:2–14s. Predicted curve apex:26s. Brighter rim/shaker motif and layered unpitched crash/low percussion impact. Same causal V2 scheduler; human salience is not yet verified.')
pair([('V2 · full mix',O/'gestures/v2.wav'),('V3 · full mix',O/'gestures/v3.wav')])
pair([('V3 · turn activation alone',O/'gestures/v3_turn_signal.wav'),('V3 · curve impact alone',O/'gestures/v3_curve_apex.wav')])
heading('J · Full native routes')
f=O/'replay_results.json'
if f.exists():
 for row in json.loads(f.read_text()):
  text(row['label']+' — Instrumented transport: '+row['summary']);
  energy=next((x for x in json.loads((O/'archive_energy.json').read_text()) if x['run']==row['run']),None) if (O/'archive_energy.json').exists() else None
  if energy:text('Quiet spans ≥1s (including intentional ending): '+str(energy['quiet_spans_at_least_1s'])+'. Transport completion does not establish musical continuity.')
  audio('Actual archived score',R/row['audio'])
else:text('New fixed-window full-route regressions pending. Earlier route successes do not establish this revision’s reliability.')
parts.append('<p><a href="INVESTIGATION.md">Detailed investigation notes</a> · <a href="../../STATUS.md">Project status</a></p>')
(O/'index.html').write_text('\n'.join(parts));print(O/'index.html')
