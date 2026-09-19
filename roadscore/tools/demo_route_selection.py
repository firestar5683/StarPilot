"""Offline cached-log demo selection. Never loaded by runtime or generation.
No network, replay, hardware, or model execution. Private manifest paths are inputs.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import warnings

import numpy as np
from openpilot.tools.lib.logreader import _LogFileReader


def runs(times, values, minimum=0., gap=.6):
  found=[];start=None;last=None;current=None
  for t,value in zip(times,values):
    if value != current or (last is not None and t-last>gap):
      if current and start is not None and last-start>=minimum:found.append({'start':float(start),'end':float(last),'value':current})
      start=t;current=value
    last=t
  if current and start is not None and last-start>=minimum:found.append({'start':float(start),'end':float(last),'value':current})
  return found


def extract(row,base):
  files={}
  for entry in row['cache'].get('files',[]):
    path=base/entry['path']
    if path.is_file() and path.name.startswith(('rlog','qlog')):
      segment=entry['segment']
      if segment not in files or path.name.startswith('rlog'):files[segment]=(path,entry)
  origin=None;first={};last={};counts=Counter();valid=Counter();gaps={};prior={};samples={k:[] for k in ['car','control','model','active','alerts','nav']};decodes=[];sourcefiles=[]
  start=row['selection']['start_s'];end=row['selection']['end_s'];last_sample={};active_prior=None;active_prior_t=None;edges=[]
  for segment,(path,entry) in sorted(files.items()):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Cache checksum mismatch')
    sourcefiles.append({'segment':segment,'path':str(path),'sha256':entry['sha256']})
    try:
      with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for e in _LogFileReader(str(path),sort_by_time=False):
          ns=int(e.logMonoTime)
          if origin is None:origin=ns
          t=(ns-origin)/1e9
          if t<start or (end is not None and t>=end):continue
          kind=e.which()
          if kind not in ('carState','controlsState','modelV2','selfdriveState','roadCameraState','navInstruction'):continue
          counts[kind]+=1;first.setdefault(kind,t);last[kind]=t
          if kind in prior:gaps[kind]=max(gaps.get(kind,0),t-prior[kind])
          prior[kind]=t
          if not e.valid:continue
          valid[kind]+=1
          data=getattr(e,kind)
          if kind=='selfdriveState':
            active=bool(data.active)
            if active_prior is not None and active!=active_prior and t-active_prior_t<1:
              edges.append({'time':t,'active':active,'state':str(data.state),'source':'selfdriveState.active'})
            active_prior=active;active_prior_t=t
          if t-last_sample.get(kind,-1e9)<.099 and kind!='navInstruction':continue
          last_sample[kind]=t
          if kind=='carState':samples['car'].append([t,float(data.vEgo),float(data.steeringAngleDeg),bool(data.leftBlinker),bool(data.rightBlinker),bool(data.standstill)])
          elif kind=='controlsState':samples['control'].append([t,float(data.curvature)])
          elif kind=='selfdriveState':
            samples['active'].append([t,active]);samples['alerts'].append([t,str(data.alertType),str(data.alertText1),str(data.alertText2),str(data.alertSize)])
          elif kind=='modelV2':
            age=(ns-int(data.timestampEof))/1e9
            trajectory=[(float(tt)-age,float(yaw)*float(v)) for tt,yaw,v in zip(data.orientationRate.t,data.orientationRate.z,data.velocity.x) if 1<=float(tt)-age<=5 and float(v)>3]
            strength=max((abs(lat) for tt,lat in trajectory),default=0)
            samples['model'].append([t,strength])
          elif kind=='navInstruction':samples['nav'].append([t,str(data.maneuverType),str(data.maneuverModifier),float(data.maneuverDistance)])
        decodes.extend({'segment':segment,'warning':str(w.message)} for w in caught)
    except Exception as error:decodes.append({'segment':segment,'error':str(error)})
  coverage={k:{'count':counts[k],'valid':valid[k],'first':first[k],'last':last[k],'max_gap':gaps.get(k)} for k in counts}
  return dict(label=row['label'],selection=row['selection'],origin_mono_ns=origin,files=sourcefiles,coverage=coverage,decode_warnings=decodes,samples=samples,engagement_edges=edges)


def characterize(data):
  s=data['samples'];car=np.asarray(s['car'],dtype=float);control=np.asarray(s['control'],dtype=float)
  if len(car)<2 or len(control)<2:return {'error':'Insufficient car/control data'}
  t=car[:,0];speed=car[:,1]
  indices=np.searchsorted(control[:,0],t,side='right')-1;indices=np.clip(indices,0,len(control)-1)
  lateral=abs(control[indices,1])*speed**2
  fresh=(t-control[indices,0]>=0)&(t-control[indices,0]<.3)
  smooth=np.convolve(np.where(fresh,lateral,0),np.ones(9)/9,mode='same')
  moving=speed>4
  curve=runs(t,((smooth>.65)&moving&fresh).tolist(),minimum=1.5)
  straight=runs(t,((smooth<.22)&(speed>5)&fresh).tolist(),minimum=7)
  for c in curve:
    sel=(t>=c['start'])&(t<=c['end']);peak=np.argmax(smooth[sel]);ct=t[sel]
    c.update(peak_time=float(ct[peak]),peak_lateral_proxy=float(smooth[sel][peak]),direction='left' if np.median(control[indices[sel],1])>0 else 'right')
    previous=[v for v in straight if 0<=c['start']-v['end']<8]
    c['preceding_straight_seconds']=max((v['end']-v['start'] for v in previous),default=0)
  signals=runs(t,['both' if r[3] and r[4] else 'left' if r[3] else 'right' if r[4] else '' for r in car],minimum=.3)
  merged=[]
  for sig in signals:
    if merged and sig['value']==merged[-1]['value'] and sig['start']-merged[-1]['end']<1.5:merged[-1]['end']=sig['end']
    else:merged.append(sig.copy())
  signals=[v for v in merged if v['end']-v['start']>=1.5]
  alerts=runs([r[0] for r in s['alerts']],[('|'.join(r[1:]) if r[1] and r[4]!='none' else '') for r in s['alerts']],minimum=.2)
  stops=runs(t,(speed<.5).tolist(),minimum=2)
  return dict(curves=curve,straights=straight,signals=signals,alerts=alerts,stops=stops,engagement_edges=data['engagement_edges'],observed_start=float(t[0]),observed_end=float(t[-1]),curve_proxy='abs(controlsState.curvature)*carState.vEgo^2 smoothed0.9s; not measured road geometry',actual_selfdrive_active_coverage=len(s['active']))


def candidates(data,events,full_logs):
  if 'error'in events:return []
  start=max(data['selection']['start_s'],events['observed_start']);end=min(data['selection']['end_s'] or events['observed_end'],events['observed_end']);result=[]
  for length in [90,120,60]:
    for begin in np.arange(math.ceil(start/5)*5,max(start,end-length)+.01,5):
      finish=begin+length
      curves=[e for e in events['curves'] if begin+5<=e['peak_time']<=finish-5]
      edges=[e for e in events['engagement_edges'] if begin+3<=e['time']<=finish-3]
      signals=[e for e in events['signals'] if begin<=e['start'] and e['end']<=finish]
      alerts=[e for e in events['alerts'] if begin<=e['start']<finish]
      build=sum(e['preceding_straight_seconds']>=7 for e in curves)
      side_diversity=len(set(e['direction'] for e in curves))
      both_edges=any(e['active'] for e in edges) and any(not e['active'] for e in edges)
      excess=max(0,len(signals)-6)+max(0,len(edges)-5)+max(0,len(curves)-5)
      score=6*min(build,2)+3*min(len(curves),3)+2*side_diversity+4*min(len(edges),3)+5*both_edges+2*min(len(signals),4)+min(len(alerts),2)-2*excess
      # Reject windows crossing missing telemetry; never mistake absence for calm.
      car=np.asarray(data['samples']['car']);times=car[(car[:,0]>=begin)&(car[:,0]<=finish),0];maxgap=float(np.max(np.diff(times))) if len(times)>1 else length
      if maxgap>.5:score-=30
      if not full_logs or data['decode_warnings']:score-=25
      result.append(dict(label=data['label'],start=float(begin),end=float(finish),duration=length,score=score,straight_to_curve_count=build,curves=curves,active_transitions=edges,signals=signals,alerts=alerts,max_car_gap=maxgap,full_logs=full_logs))
  return sorted(result,key=lambda v:v['score'],reverse=True)


def main():
  parser=argparse.ArgumentParser();parser.add_argument('manifest',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
  args.output.mkdir(parents=True,exist_ok=True);m=json.loads(args.manifest.read_text());ranking=[]
  for row in m['routes']:
    path=args.output/(row['label']+'.telemetry.private.json')
    if path.exists():data=json.loads(path.read_text())
    else:data=extract(row,args.manifest.parent);path.write_text(json.dumps(data))
    events=characterize(data)
    analysis=json.loads((args.manifest.parent/'analysis'/f"{row['label']}.private.json").read_text())
    ranked=candidates(data,events,analysis.get('complete_selected_logs',False))
    (args.output/(row['label']+'.events.private.json')).write_text(json.dumps(dict(events=events,candidates=ranked[:12]),indent=2))
    if ranked:ranking.append(ranked[0])
    print(row['label'],'events',len(events.get('curves',[])),len(events.get('signals',[])),len(events.get('engagement_edges',[])),'best',ranked[0]['score'] if ranked else None,flush=True)
  (args.output/'ranking.private.json').write_text(json.dumps(sorted(ranking,key=lambda v:v['score'],reverse=True),indent=2))
if __name__=='__main__':main()
