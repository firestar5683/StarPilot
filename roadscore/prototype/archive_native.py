"""Archive the same app's local final render with its actual local DAC origin."""
import json,shutil,sys
from pathlib import Path
import soundfile as sf
from score_archive import archive
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);route=sys.argv[2];start=int(sys.argv[3]);run=root/'results/current'
with sf.SoundFile(run/'heard.wav') as source, sf.SoundFile(out/'host_heard.flac','w',samplerate=source.samplerate,channels=source.channels,subtype='PCM_16') as target:
 while len(block:=source.read(48000,dtype='int16')):target.write(block)
blocks=[json.loads(x) for x in (run/'audio_blocks.jsonl').read_text().splitlines()]
if not blocks:raise RuntimeError('No final audio blocks; refusing empty archive')
for b in blocks:b.update(host_audio_s=b['audio_s'],host_dac_wall=b['callback_wall']+b['dac_delay'],presentation_host='comma')
(out/'host_audio.jsonl').write_text(''.join(json.dumps(b)+'\n' for b in blocks))
(out/'host_audio_summary.json').write_text(json.dumps({'first_host_dac_wall':blocks[0]['host_dac_wall'],'presentation_host':'comma','muted':blocks[0]['muted'],'portaudio_flags':sum(bool(b.get('portaudio_status')) for b in blocks)}))
for name in ['summary.json','jobs.jsonl','boundaries.jsonl','ending.json','bridge.json','trace.jsonl','runtime_manifest.json','song_form.json','gesture_grid.json','gestures.json','composition.json','quality_events.jsonl']:
 if (run/name).exists():shutil.copy2(run/name,out/name)
if (run/'quality').exists():shutil.move(str(run/'quality'),str(out/'quality'))
if (root/'generated/ace_link.jsonl').exists():shutil.copy2(root/'generated/ace_link.jsonl',out/'ace_link.jsonl')
print(archive(route,out,start))
