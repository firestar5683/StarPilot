"""Package private saved captures; camera alignment from callback/DAC evidence."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'results/continuity'
for kind,start,seconds,source in [('curve',110,100,'demo'),('arrival',170,87,'arrival')]:
 run=O/f'live_{kind}'
 if not (run/'summary.json').exists():continue
 out=O/f'{kind}_demo.mp4'
 blocks=[json.loads(t) for t in (run/'audio_blocks.jsonl').read_text().splitlines()]
 b=blocks[0];offset=b['callback_wall']+b['dac_delay']-b['replay_origin_wall']-start
 if not out.exists():
  subprocess.run(['ffmpeg','-v','error','-i',str(R/'assets'/f'{source}.mp4'),'-itsoffset',str(offset),'-i',str(run/'heard.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(seconds),str(out)],check=True)
 subprocess.run([sys.executable,str(R/'prototype/package_review.py'),str(run),out.name,str(start),str(O/f'{kind}_review.html')],check=True)
 (O/f'{kind}_alignment.json').write_text(json.dumps({'audio_delay_seconds':offset,'source':'First captured callback monotonic time plus reported DAC delay relative to replay origin. Original prepared video accounts for camera/log offset. Software timing only, speaker muted.','video_seconds':seconds},indent=2))
