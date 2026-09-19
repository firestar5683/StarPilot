"""Route-owned exact rendered score and compact decisions; no regeneration recipe."""
import json,shutil,subprocess,time
from pathlib import Path
from route_library import ROOT,identity

def prefer_new_score(new,old):
 def coverage(m):return (bool(m.get('full_route')) and m.get('replay_start_seconds',0)==0,m.get('replay_start_seconds',0)==0,float(m.get('audio_seconds',0)))
 if coverage(new)[0] and coverage(old)[0]:return True
 return coverage(new)>=coverage(old)

def archive(route,run,start=0):
 dongle,name=identity(route);parent=ROOT/'routes'/dongle/name/'roadscore';parent.mkdir(parents=True,exist_ok=True)
 dest=parent/run.name;dest.mkdir(exist_ok=False)
 shutil.move(str(run/'host_heard.flac'),str(dest/'score.flac'))
 (run/'host_heard.flac').symlink_to(dest/'score.flac')
 if (run/'quality').exists():
  shutil.move(str(run/'quality'),str(dest/'quality'));(run/'quality').symlink_to(dest/'quality',target_is_directory=True)
 for filename in ['host_audio.jsonl','host_audio_summary.json','clock_sync.json','clock_sync_after.json','launch.json','summary.json','jobs.jsonl','boundaries.jsonl','ending.json','bridge.json','runtime_manifest.json','song_form.json','gesture_grid.json','gestures.json','composition.json','settings.json','quality_events.jsonl','ace_link.jsonl']:
  if (run/filename).exists():shutil.copy2(run/filename,dest/filename)
 blocks=[b for x in (run/'host_audio.jsonl').read_text().splitlines() if (b:=json.loads(x)).get('audio_s') is not None]
 # The first model's absolute time relative to native route start is recorded by sender.
 timing=json.loads((run/'replay_origin.json').read_text()) if (run/'replay_origin.json').exists() else {}
 audio_stats=json.loads((run/'host_audio_summary.json').read_text())
 origin_audio=(blocks[0]['host_audio_s']-blocks[0]['audio_s']) if blocks else 0
 version=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True)
 checkpoint=version.stdout.strip() if version.returncode==0 else ((ROOT/'CHECKPOINT').read_text().strip() if (ROOT/'CHECKPOINT').exists() else 'unknown')
 meta={'route':route,'created':time.time(),'checkpoint':checkpoint,'backend':'native tinygrad Stable Audio 3 Small-Music','music_checkpoint':checkpoint,'source_identity_checkpoint':None,'sample_rate':48000,'channels':2,'replay_start_seconds':start,'first_model_ns':timing.get('first_model_ns'),'audio_zero_host_seconds':origin_audio,'audio_file_start_relative_first_model':audio_stats['first_host_dac_wall']-timing['host_received_wall'] if timing else None,'presentation_host':audio_stats.get('presentation_host','development host'),'presentation':'host final rendered PCM; muted runs capture the identical pre-mute stream','synchronization':'first original model logMonoTime anchors replay; sample offsets preserved','complete':bool(blocks),'live_realdata_recording':False}
 if (run/'runtime_manifest.json').exists():
  manifest=json.loads((run/'runtime_manifest.json').read_text());meta['source_identity']=manifest.get('source_identity',{'note':'See runtime manifest; source hash unavailable in this older run'});meta['backend']=manifest.get('backend',meta['backend']);meta['composer']=manifest.get('composer','sa3');meta['profile']=manifest.get('ace_initial_provenance',{}).get('prepared_profile')
 launch=json.loads((run/'launch.json').read_text()) if (run/'launch.json').exists() else {}
 meta['full_route']=launch.get('end_reason')=='native final segment exhausted' and start==0
 meta['audio_seconds']=blocks[-1]['audio_s']+.1 if blocks else 0
 meta['output_underruns']=audio_stats.get('portaudio_flags',0)
 meta['capture_timing_clean']=not any(audio_stats.get(k,0) for k in ['portaudio_flags','starved_callbacks','late_frames'])
 if not meta['capture_timing_clean']:meta['timing_limitation']='Lossless rendered PCM and per-block DAC timing are retained. Hardware output interruptions are not reproduced by contiguous stored playback.'
 (dest/'metadata.json').write_text(json.dumps(meta,indent=2))
 # Compact phase/nav decisions rather than duplicate every underlying model message.
 last=None
 with (dest/'events.jsonl').open('w') as out:
  for b in blocks:
   event={k:b.get(k) for k in ['route_t','audio_s','phase','kind','activation','strength','predicted_peak','cadence_entry_audio_s']}
   key=tuple(event.get(k) for k in ['phase','kind','activation','cadence_entry_audio_s'])
   if key!=last:out.write(json.dumps(event)+'\n');last=key
 if (run/'trace.jsonl').exists():
  last=None
  with (dest/'decisions.jsonl').open('w') as out:
   for line in (run/'trace.jsonl').open():
    row=json.loads(line);nav=row.get('nav',{})
    key=(row.get('phase'),row.get('kind'),row.get('activation'),row.get('nav_revision'),nav.get('type'),nav.get('modifier'),row.get('arrival_at'),row.get('completed_jobs'),row.get('playing_identity'))
    if key!=last:
     event={k:row.get(k) for k in ['route_t','elapsed','phase','kind','activation','strength','predicted_peak','playing_identity','completed_jobs','nav','nav_revision','arrival_at','source_cutoff_ns','command_wall']};out.write(json.dumps(event)+'\n');last=key
 old={}
 try:
  previous=parent/json.loads((parent/'latest.json').read_text())['session'];old=json.loads((previous/'metadata.json').read_text())
  if 'audio_seconds' not in old:old['audio_seconds']=json.loads((previous/'summary.json').read_text()).get('audio_seconds',0)
 except (OSError,KeyError,ValueError):pass
 (parent/'last_generated.json').write_text(json.dumps({'session':dest.name}))
 if prefer_new_score(meta,old):(parent/'latest.json').write_text(json.dumps({'session':dest.name}))
 return dest

def latest(route):
 dongle,name=identity(route);parent=ROOT/'routes'/dongle/name/'roadscore';index=json.loads((parent/'latest.json').read_text());path=parent/index['session']
 if path.parent!=parent:raise ValueError('Invalid score index')
 return path
