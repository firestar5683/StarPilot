"""Finish a single private listening gate from preserved artifacts, without autoplay."""
import json,html,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'results/overnight';page=O/'index.html';text=page.read_text();run=R/'results/normal_1789525740';audit=json.loads((run/'overnight_audit.json').read_text())
# The review references private local captures only; route files are never published.
text+='<h2>D. Normal replay and archived musical decisions</h2><p>Actual normal UI, camera and path. The soundtrack is the exact archived fresh-generation score; this recorded review replay bypassed Chestnut. The overlay shows historical section decisions.</p><video controls preload="none" style="width:100%" src="../normal_1789526728/synchronized.mp4"></video>'
text+='<h2>G. Arrival / outro</h2><p>Arrival was inferred from delivered navigation and parked standstill, with a resolving runway before silence. No route timestamp configured the runtime.</p>'
if (O/'arrival_outro.wav').exists():text+='<audio controls preload="none" src="arrival_outro.wav"></audio>'
text+='<h2>H. Mac stability</h2><p>Full community route: 571.8 seconds; zero host starvation, late/dropped samples, sequence gaps, output flags, renderer underruns or emergency repeats. Maximum host alignment error 0.606 ms. Minimum source buffer 10.05 s. All output was physically muted. A clean run is not proof against every future network interruption.</p>'
text+='<h2>I. Startup</h2><p>Uncached process-cold worker: 127.0 s; full launcher: 145.2 s. Removing the second complete generation saved redundant work. Initial snapshot restore: 62.5 s, REJECTED after failed equivalence; its musical outputs are excluded. A measured post-boot lower bound is not established.</p>'
text+='<details><summary>Objective evidence and limitations</summary><pre>'+html.escape(json.dumps({k:audit[k] for k in ['stream','runtime','fresh_jobs_heard','transition_timing']},indent=2))+'</pre><p>Roles and bars remain musical hypotheses. Sample-accurate scheduling does not prove correct downbeat or harmonic coherence. Physical speaker evaluation is deferred.</p></details>'
page.write_text(text)
