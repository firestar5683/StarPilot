from pathlib import Path
import json,html
P=Path(__file__).resolve().parent;R=P.parents[1];O=R/'results/ace_chestnut_20260916'
def audio(path,label):return f'<figure><figcaption>{html.escape(label)}</figcaption><audio controls preload="none" src="{html.escape(path)}"></audio></figure>'
p=['''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RoadScore · ACE Chestnut</title><style>body{font:17px/1.5 system-ui;background:#10141d;color:#e7edf5;max-width:1050px;margin:auto;padding:36px}h1,h2{line-height:1.2}h2{margin-top:48px;color:#95dbca}a{color:#95c9ff}audio{width:100%}figure{margin:20px 0;padding:18px;background:#1c2533;border-radius:12px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;text-align:left;border-bottom:1px solid #354052}.note{padding:18px;background:#243249;border-radius:12px}nav{display:flex;gap:18px;flex-wrap:wrap}</style><h1>ACE-Step on Chestnut</h1><p>Private engineering and listening review. All files were generated/rendered with physical audio muted. Nothing autoplays.</p><nav>''']
p+=['<a href="#'+s+'">'+s+'</a>' for s in 'ABCDEFG'];p+=['</nav><p class="note">Human preference is established for the original Mac ACE music. The new native port, transitions, outro, and gestures still require listening approval. Prepared conditioning is currently made on the Mac; heavy generation and decoded audio below run on Chestnut. No modeld coexistence approval. The first45s run hit a USB timeout; an explicitly synchronized45s retry completed, but a90s decode later hung. Sustained stability remains unresolved.</p>']
p+=['<h2 id="A">A · Accepted ACE reference</h2>',audio('../composition_20260916/ace/structured90.wav','Known-good 90-second Mac reference'),audio('../composition_20260916/ace/verse_to_chorus.wav','Human-approved verse → chorus')]
p+=['<h2 id="B">B · Native Chestnut music</h2><p>FP16, existing tinygrad tensor-core padding, eight-step Euler; DCW disabled. Times below exclude conditioning preparation and startup. Cold compilation is several minutes.</p><table><tr><th>Audio</th><th>Generation</th><th>Decode</th><th>Total</th><th>RTF</th><th>Tracked GPU</th></tr>']
for d in [15,30,45,60,90]:
 q=O/f'reference{d}'/'bounded_result.json'
 if not q.exists():q=O/f'reference{d}'/'chestnut_result.json'
 if q.exists():
  r=json.loads(q.read_text());p.append(f'<tr><td>{d}s</td><td>{r["generation_seconds"]:.2f}s</td><td>{r["decode_seconds"][-1]:.2f}s</td><td>{r["total_warm_seconds"]:.2f}s</td><td>{r["total_warm_rtf"]:.3f}</td><td>{r["tracked_gpu_bytes"]/1e9:.2f} GB</td></tr>')
p.append('</table>')
for d in [15,30,45,60,90]:
 if (O/f'reference{d}/chestnut.wav').exists():p.append(audio(f'reference{d}/chestnut.wav',f'{d}s · native Chestnut generation + decode'+(' · decode recovered in a later process; exact RTF unavailable' if d==90 else '')))
p+=['<h2 id="C">C · Precision and decoder comparison</h2><p>Full DiT: relative RMSE0.428% versus official FP32. Native full-length VAE: relative RMSE0.089%. The first optimized FP16-reference maximum-error check failed narrowly; the preserved FP32 audit is linked below. Quantized weights are an unapproved experiment, not the default.</p><p><a href="tc2_precision_audit.json">Precision audit</a> · <a href="reference15/decode_comparison.json">Decoder audit</a></p>',audio('reference15/official_decode.wav','Same Chestnut latents · official Mac decoder')]
p.append('<p>INT8 storage was rejected: slower startup, unchanged resident memory, extra weight error. Evidence is retained without promoting it as a listening candidate.</p>')
p+=['<h2 id="D">D · Section continuity</h2><p>Reference-conditioned independent roles are not proof of continuation. New sequential flow uses the previous section’s actual latent tail as the preserved prefix.</p>']
if (O/'flow/section_flow.wav').exists():p.append(audio('flow/section_flow.wav','Native verse → prechorus → chorus → bridge → outro'))
else:p.append('<p>Sequential native flow is still under test.</p>')
p+=['<h2 id="E">E · Arrival</h2><p>Existing musical context → generated outro → source-derived final cadence. The explanatory render is separate from a road acceptance run.</p>']
if (O/'flow/arrival.wav').exists():p.append(audio('flow/arrival.wav','Native outro and deterministic final cadence'))
else:p.append('<p>Native repaint outro is still under test.</p>')
p+=['<h2 id="F">F · Gestures V2</h2><p>Controlled synthetic timeline: signal2–14s; curve preparation20s / predicted peak26s; navigation32s; lane-change example36s; stop40s; resume44s; outro53s. V2 changes timbre and phrase structure, not merely gain. No guessed notes are introduced.</p>',audio('gestures/dry.wav','Dry ACE source'),audio('gestures/v1.wav','Previous gesture bank'),audio('gestures/v2.wav','V2 · same source and events')]
for kind in ['turn_signal','turn_signal_sustain','turn_signal_off','curve_prepare','curve_apex','navigation_turn','lane_change','stop','resume']:p.append(audio('gestures/v2_'+kind+'.wav',kind.replace('_',' ').title()))
p+=[audio('road_gestures/v1.flac','Full archived road capture · previous gestures'),audio('road_gestures/v2.flac','Same archived dry music and causal states · gestures V2')]
p+=['<h2 id="G">G · Normal replay and fallback</h2><p>ACE is opt-in with <code>--composer ace</code>; the normal default remains SA3. These are fresh runtime tests, separate from the archived gesture remix. All physical outputs were muted. No modeld/real-driving coexistence test was performed.</p>']
for name,label in [('mac_replay_audit.json','Mac fresh ACE'),('native_replay_audit.json','Native comma fresh ACE'),('sa3_replay_audit.json','Mac fresh fallback SA3')]:
 q=O/name
 if not q.exists():continue
 r=json.loads(q.read_text());h=r['host_audio'];rtf=r.get('rtf_per_new_audio',[])
 summary=f"{r['audio_seconds']:.1f}s captured; {r['completed_jobs']} new sections; RTF {min(rtf):.3f}–{max(rtf):.3f}" if rtf else 'No fresh generation measured'
 p.append(f'<p><strong>{label}: {"instrumented pass" if r["instrumented_pass"] else "not a clean pass"}</strong>. {summary}. Composer fallbacks {r["fallbacks"]}; renderer underflows {r["underflows"]}; host late samples {h.get("late_frames",0)}; host starvation callbacks {h.get("starved_callbacks",0)}; output flags {h.get("portaudio_flags",0)}. <a href="{name}">Full evidence</a>.</p>')
for name,label in [('mac_stored_summary.json','Mac stored fallback score'),('native_stored_summary.json','Native stored ACE score')]:
 q=O/name
 if q.exists():
  r=json.loads(q.read_text());p.append(f'<p>{label}: contiguous samples verified={r["contiguous_samples_verified"]}; output flags={r["portaudio_flags"]}; clock alignment error={r["max_clock_alignment_error_seconds"]*1000:.2f}ms; generation invoked={r["generation_invoked"]}. <a href="{name}">Evidence</a>.</p>')
if (O/'road_demo.json').exists():
 r=json.loads((O/'road_demo.json').read_text());p.append(audio(r['audio'],'Actual native ACE route score · gestures and arrival'));p.append(audio(r['audio'].replace('score.flac','arrival_excerpt.wav'),'Actual road arrival excerpt · 178–252s'))
p.append('<p>The Mac fresh ACE run preserved a transport-timing failure. It is not hidden by the successful model throughput or contiguous stored playback. Subjective continuity, ending quality and gesture salience remain for human review.</p><p><a href="../../ACE_CHESTNUT.md">Engineering report and limitations</a> · <a href="../composition_20260916/index.html">Previous road evidence</a> · <a href="regression_route.log">Actual route causality check</a></p>')
(O/'index.html').write_text('\n'.join(p));print(O/'index.html')
