"""Build an optional full-resolution software-decode cache from local route assets."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def probe(path, ffprobe):
  args=[ffprobe,'-v','error','-select_streams','v:0','-count_frames','-show_entries',
        'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,duration','-of','json',str(path)]
  return json.loads(subprocess.check_output(args))['streams'][0]


def nominal_rate(value):
  exact=Fraction(value);rate=exact.limit_denominator(1001)
  if rate<=0 or abs(float(rate-exact))>1e-5:
    raise ValueError('Cannot establish a stable source frame rate')
  return rate


def validate_output(source, output, timestamps):
  rate=nominal_rate(source['r_frame_rate']);count=int(source['nb_read_frames'])
  if output['codec_name']!='h264' or int(output['nb_read_frames'])!=count:
    raise ValueError('Output frame count or codec differs')
  if any(output[key]!=source[key] for key in ('width','height')):
    raise ValueError('Resolution differs')
  if Fraction(output['avg_frame_rate'])!=rate:
    raise ValueError('Output frame rate differs')
  tolerance=1/90000+1e-6
  if len(timestamps)!=count or any(abs(t-i/float(rate))>tolerance for i,t in enumerate(timestamps)):
    raise ValueError('Output timestamps are not aligned with source frame indices')
  if abs(float(output['duration'])-count/float(rate))>tolerance:
    raise ValueError('Output duration differs')
  return {'codec':'h264','source_frames':count,'output_frames':count,'width':source['width'],'height':source['height'],
          'frame_order_verified':True,'timing_verified':True,'rate':str(rate),
          'duration':count/float(rate),'verification':'one-to-one sequential transcode; no frame filters, passthrough timing, no B frames; decoded counts and every output PTS checked'}


def build(parent, ffmpeg='ffmpeg', ffprobe='ffprobe', reserve_bytes=1024**3):
  parent=Path(parent).resolve();original=json.loads((parent/'cache_manifest.json').read_text())
  dest=parent/'playback';dest.mkdir(exist_ok=True)
  marker=dest/'.acquiring'
  if marker.exists():raise RuntimeError('Playback cache already being built or needs inspection')
  with marker.open('x') as stream:stream.write(str(os.getpid()))
  manifest={'schema':'roadscore-playback-cache-v1','route':original['route'],'complete':False,'files':[]}
  try:
    for item in original['files']:
      rel=Path(item['path'])
      if rel.is_absolute() or '..' in rel.parts or len(rel.parts)!=2:raise ValueError('Invalid source path')
      source=parent/rel;before=source.stat()
      if before.st_size!=item['bytes']:raise ValueError('Original manifest size mismatch')
      target_rel=rel.with_name('fcamera.ts') if rel.name=='fcamera.hevc' else rel
      target=dest/target_rel;target.parent.mkdir(exist_ok=True)
      entry={'source':str(rel),'path':str(target_rel),'source_bytes':before.st_size,'source_mtime_ns':before.st_mtime_ns}
      if rel.name=='fcamera.hevc':
        info=probe(source,ffprobe);rate=nominal_rate(info['r_frame_rate'])
        if target.exists():raise RuntimeError('Derived video already exists; inspect before rebuilding')
        if shutil.disk_usage(dest).free<reserve_bytes+before.st_size*3:
          raise RuntimeError('Insufficient disk reserve for next video segment')
        temporary=target.with_suffix('.partial.ts')
        subprocess.run([ffmpeg,'-v','error','-nostdin','-threads','2','-r',str(rate),'-i',str(source),
          '-an','-c:v','libx264','-threads','2','-preset','ultrafast','-tune','zerolatency','-crf','20',
          '-pix_fmt','yuv420p','-profile:v','baseline','-x264-params',
          'keyint=20:min-keyint=20:scenecut=0:bframes=0:ref=1:cabac=0','-fps_mode','passthrough',
          '-bsf:v',f'h264_metadata=tick_rate={rate*2}:fixed_frame_rate_flag=1',
          '-muxdelay','0','-muxpreload','0','-f','mpegts',str(temporary)],check=True)
        temporary.rename(target)
        out=probe(target,ffprobe)
        stamps=json.loads(subprocess.check_output([ffprobe,'-v','error','-select_streams','v:0',
          '-show_packets','-show_entries','packet=pts_time','-of','json',str(target)]))['packets']
        entry['video_validation']=validate_output(info,out,[float(x['pts_time']) for x in stamps])
        with target.open('rb') as stream:entry['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        print(f"Validated {rel.parent}: {entry['video_validation']['output_frames']} frames",flush=True)
      elif not target.exists():target.symlink_to(source)
      after=source.stat()
      if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('Original changed during conversion')
      entry['bytes']=target.stat().st_size;manifest['files'].append(entry)
    manifest['complete']=True
    temporary=dest/'playback_manifest.json.tmp';temporary.write_text(json.dumps(manifest,indent=2)+'\n')
    temporary.replace(dest/'playback_manifest.json')
  finally:
    marker.unlink()
  return dest


if __name__=='__main__':
  p=argparse.ArgumentParser(description=__doc__);p.add_argument('route_cache')
  p.add_argument('--ffmpeg',default='ffmpeg');p.add_argument('--ffprobe',default='ffprobe')
  a=p.parse_args();print(build(a.route_cache,a.ffmpeg,a.ffprobe))
