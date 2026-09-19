"""Build an entirely local, click-to-play review page from saved evidence."""
import json,sys
from pathlib import Path

run=Path(sys.argv[1]);video=sys.argv[2];start=float(sys.argv[3]);out=Path(sys.argv[4])
trace=[json.loads(line) for line in (run/'trace.jsonl').read_text().splitlines()]
data=json.dumps(trace[::2],separators=(',',':')).replace('<','\\u003c')
html='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>RoadScore · private recorded evidence</title>
<style>body{font:18px system-ui;background:#111821;color:#e8f0f7;max-width:1100px;margin:24px auto;padding:0 20px}video{width:100%;background:black}#phase{font-size:32px;color:#7be5c1}small{color:#b3c0ce}.grid{display:flex;gap:24px;flex-wrap:wrap}.grid>div{flex:1;min-width:270px}progress{width:100%;height:24px}</style>
<h1>RoadScore <small>PRIVATE · saved run</small></h1>
<p>Press play to hear the captured render on this computer. No audio starts automatically.</p>
<video id="v" controls playsinline preload="metadata" src="VIDEO"></video>
<div class="grid"><div><p id="phase"></p><progress id="amount" max="1"></progress><p id="event"></p></div><div><p id="music"></p><p id="nav"></p></div></div>
<p>The driving predictions are historical. Chestnut generated the continuations live during this recorded run; the CPU Conductor applied the causal phrase-echo build and release. Disclosed four-second source anchors connect SA3-generated passages. These displays show saved runtime decisions, not new predictions.</p>
<small>Device speakers were muted. Video is aligned using camera timestamps; source publication has measured scheduling jitter. This is rendered audio evidence, not a microphone recording. Arrival combines a generated closing with a locally timed source-informed sonority; musical acceptance remains a listening judgment.</small>
<script>
const rows=DATA,start=START,v=document.getElementById('v');
const el=id=>document.getElementById(id);
function update(){const t=start+v.currentTime;let lo=0,hi=rows.length;while(lo<hi){const m=(lo+hi)>>1;if(rows[m].route_t<=t)lo=m+1;else hi=m}const s=rows[Math.max(0,lo-1)];
el('phase').textContent=(s.kind+' · '+s.phase).toUpperCase();el('amount').value=s.amount;
el('event').textContent=`Route ${t.toFixed(2)} s · prediction ${s.lead==null?'—':s.lead.toFixed(2)+' s ahead'} · model age ${(s.model_age*1000).toFixed(0)} ms`;
el('music').textContent=`${s.playing_identity||'legacy'} · ${s.buffered.toFixed(1)} s buffered · ${s.completed_jobs} accepted continuations · ${s.fallbacks} loops · ${s.underflows} output flags`;
el('nav').textContent=s.arrival_at!=null?'Final resolution triggered':s.nav?.valid?`Navigation: ${s.nav.type} ${s.nav.modifier} · ${s.nav.remaining.toFixed(0)} m remaining`:'No current navigation';requestAnimationFrame(update)}update();
</script>'''
out.write_text(html.replace('VIDEO',video).replace('DATA',data).replace('START',str(start)))
print(out)
