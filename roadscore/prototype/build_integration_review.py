"""Build a private offline integration/status page; no autoplay or external assets."""
import html,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];out=R/'results/integration';out.mkdir(exist_ok=True)
rows=json.loads(subprocess.check_output([sys.executable,str(R/'prototype/route_library.py'),'inventory'],text=True));(out/'library_status.json').write_text(json.dumps(rows,indent=2))
body=[]
for row in rows:
 route=row['route'];base=R/'routes'/route;score='Not yet recorded'
 if (base/'roadscore/latest.json').exists():
  session=json.loads((base/'roadscore/latest.json').read_text())['session'];url='../../routes/'+route+'/roadscore/'+session
  score=f'<a href="{url}/metadata.json">Metadata</a> · <a href="{url}/score.flac">Final audio</a>'
 if row.get('stored_score_capture_timing_clean') is False:score+='<br><span class="muted">Recorded output interruption; see metadata.</span>'
 body.append('<tr>'+''.join('<td>'+str(v)+'</td>' for v in [html.escape(route),row['segments'],'Ready' if row['complete_remote_listing_cached'] and row['messages_verified'] and row['camera_present'] else 'Incomplete',html.escape(row['navigation']),html.escape(row['normal_replay']),score])+'</tr>')
first=json.loads((out/'first_attempt/result.json').read_text())
page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RoadScore integration review</title><style>body{font:16px/1.5 system-ui;background:#10151e;color:#e7edf6;margin:0;padding:36px;max-width:1300px}h1{font-size:32px}h2{margin-top:32px}a{color:#90c7ff}p{max-width:850px}.pass{background:#173c32;color:#abf0cf;padding:14px 20px;border-radius:10px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #344154;padding:12px}td:first-child{overflow-wrap:anywhere;max-width:280px}pre{white-space:pre-wrap;background:#192333;padding:18px;border-radius:8px}.muted{color:#b1bfd0}</style></head><body><h1>RoadScore — integration review</h1><p class="pass">First unseen cold launch: passed without intervention.</p><p>The route was launched by ID through the unmodified f3216fa resolver before inspection or library caching. '''+str(first['fresh_jobs'])+''' fresh Chestnut jobs, camera/path/lane rendering, navigation and curve responses were observed.</p><p><a href="first_attempt/result.json">Immutable first result</a> · <a href="../../STATUS.md">Current status and limits</a> · <a href="../../INTEGRATION.md">Detailed evidence</a></p><h2>Private offline route library</h2><table><thead><tr><th>Route</th><th>Segments</th><th>Logs / cameras / messages</th><th>Navigation</th><th>Normal replay</th><th>Recorded score</th></tr></thead><tbody>'''+''.join(body)+'''</tbody></table><h2>One command, host-owned presentation</h2><pre>./onroad --routeid 'DONGLE/ROUTE' --roadscore
./onroad --routeid 'DONGLE/ROUTE' --roadscore --replay
./routes-tool inventory</pre><p>Run from ~/Desktop/RoadScore on Mac or /data/roadscore on comma. Fresh scoring uses Chestnut. Stored-score replay does not. Add --audible to play on the host running the command. Automated runs remain muted.</p><p class="muted">The actual normal UI was instrumented on both hosts. The physical comma screen and acoustic output still need human confirmation. Native replay uses the existing software video decoder. Live logger/pruning integration and modeld coexistence are not implemented.</p><h2>Music remains frozen</h2><p><a href="../unattended/listen.html">Do the listening review at results/unattended/listen.html before the next musical prompt.</a></p></body></html>'''
(out/'index.html').write_text(page)
print(out/'index.html')
