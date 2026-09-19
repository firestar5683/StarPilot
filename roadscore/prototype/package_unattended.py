"""Package measured software-aligned camera/audio review; never modifies captured WAVs."""
import argparse,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';p=argparse.ArgumentParser();p.add_argument('--capture',default='native_final');a=p.parse_args();cap=O/a.capture
if (cap/'synchronized_timing.json').exists():
 timing=json.loads((cap/'synchronized_timing.json').read_text());offset=timing['first_output_route_t']-110
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(R/'assets/demo.mp4'),'-itsoffset',str(offset),'-i',str(cap/'heard.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','100',str(O/'curve_synchronized.mp4')],check=True)
 (O/'curve_alignment.json').write_text(json.dumps({'capture':a.capture,'audio_delay':offset,'clock_uncertainty':timing['output_uncertainty_seconds'],'note':'Only valid as a constant-offset presentation if the final capture has no underruns and callback timing stays on its sample clock. Original camera preparation accounts for camera/log offset. Normal UI separately verified by own draw instrumentation.'},indent=2))
