"""Offline VFR UI/audio mux using observed UI-frame and archived sample timestamps."""
import argparse,json,subprocess
from fractions import Fraction
from pathlib import Path
import av
from capture_alignment import audio_alignment,video_frames
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
frames=[json.loads(x) for x in (run/'ui_frames.jsonl').read_text().splitlines()];assert frames
selected=video_frames(run,frames);selected_set=set(selected);kept=[frames[i] for i in selected]
origin=kept[0]['wall'];source=av.open(str(run/'normal_ui.mp4'));target=av.open(str(run/'ui_timed.mp4'),'w');stream=target.add_stream('libx264',rate=60);stream.width=source.streams.video[0].width;stream.height=source.streams.video[0].height;stream.pix_fmt='yuv420p';stream.options={'crf':'20','preset':'fast'};clock_base=Fraction(1,1000000);stream.time_base=clock_base;stream.codec_context.time_base=clock_base;stream.codec_context.max_b_frames=0;count=0;last_pts=-1
for i,frame in enumerate(source.decode(video=0)):
 if i>=len(frames):break
 if i not in selected_set:continue
 frame.pts=max(last_pts+1,round((frames[i]['wall']-origin)*1000000));last_pts=frame.pts;frame.time_base=clock_base
 for packet in stream.encode(frame):target.mux(packet)
 count+=1
for packet in stream.encode():target.mux(packet)
target.close();source.close()
score,start,muted,kind=audio_alignment(run,origin)
assert count==len(kept), 'UI frame metadata/video count mismatch'
duration=kept[-1]['wall']-origin
out=run/'synchronized.mp4'
audio_offset=['-ss',str(start)] if start>=0 else ['-itsoffset',str(-start)]
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(run/'ui_timed.mp4'),*audio_offset,'-i',str(score),'-map','0:v','-map','1:a','-t',str(duration),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)],check=True)
(run/'synchronization.json').write_text(json.dumps({'ui_frames':count,'duration':duration,'score_file_start_seconds':max(0,start),'initial_audio_delay_seconds':max(0,-start),'method':'Observed UI-frame wall timestamps converted to VFR; samples aligned to measured '+kind,'max_ui_frame_gap_seconds':max(b['wall']-a['wall'] for a,b in zip(kept,kept[1:])),'physical_output_muted':muted,'timing_uncertainty':'UI draw/readback timing, approximately one frame; no physical speaker validation'},indent=2));print(out)
