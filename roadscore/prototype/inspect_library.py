"""Post-acceptance inventory audit only. Runtime never imports these results."""
import collections,json
from pathlib import Path
from route_library import ROOT,local_source,inventory
from openpilot.tools.lib.logreader import LogReader
for item in inventory():
 route=item['route'];source=Path(item['source']);name=route.split('/')[1];counts=collections.Counter();segments=[]
 for segment in sorted(source.glob(name+'--*')):
  logs=list(segment.glob('rlog*')) or list(segment.glob('qlog*'));row={'segment':segment.name,'files':{p.name:p.stat().st_size for p in segment.iterdir() if p.is_file()}}
  try:
   c=collections.Counter(e.which() for e in LogReader(str(logs[0])));counts.update(c);row['services']=dict(c)
  except Exception as error:row['error']=str(error)
  segments.append(row)
 report={'route':route,'purpose':'post-acceptance inventory; not consumed at runtime','services':dict(counts),'segments':segments,'required_present':all(counts[x]>0 for x in ['modelV2','carState','roadEncodeIdx']),'navigation_present':counts['navInstruction']>0,'nav_route_present':counts['navRoute']>0}
 destination=ROOT/'routes'/route/'inventory.json';destination.write_text(json.dumps(report,indent=2));print('AUDITED',route,report['required_present'],report['navigation_present'],flush=True)
