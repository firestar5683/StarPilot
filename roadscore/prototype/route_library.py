"""Private native-layout route cache. Does not feed pre-analysis to RoadScore."""
import argparse,json,os,re,shutil,hashlib
from pathlib import Path
from playback_cache import validated_playback
ROOT=Path(__file__).resolve().parents[1]
def identity(route):
 parts=route.replace('|','/').split('/')
 if len(parts)!=2 or not re.fullmatch(r'[a-f0-9]{16}',parts[0]) or not re.fullmatch(r'[A-Za-z0-9_-]{20}',parts[1]):raise ValueError('Expected DONGLE/ROUTE')
 return parts

def cache_complete(parent):
 manifest=parent/'cache_manifest.json'
 if not manifest.exists():return None
 try:
  entries=json.loads(manifest.read_text())['files']
  return bool(entries) and all((parent/x['path']).is_file() and (parent/x['path']).stat().st_size==x['bytes'] for x in entries)
 except (OSError,ValueError,KeyError):return False

def local_source(route,root=ROOT):
 dongle,name=identity(route)
 candidates=[root/'routes'/dongle/name,root/'routes'/dongle,root/'routes']
 candidates += [Path(x) for x in os.environ.get('ROADSCORE_ROUTE_PATHS','/data/media/0/realdata').split(':') if x]
 for parent in candidates:
  if (parent/'.acquiring').exists() or cache_complete(parent) is False:continue
  if any(parent.glob(name+'--*/rlog*')) or any(parent.glob(name+'--*/qlog*')):return validated_playback(parent,route) or parent
 from cache_discovery import prepared_source
 parent=prepared_source(route,root)
 return (validated_playback(parent,route) or parent) if parent is not None else None

def fetch(route):
 # Same authenticated endpoints and host fallback as native replay. Never prints signed URLs.
 from openpilot.tools.lib.api import CommaApi,route_api_hosts,APIError
 from openpilot.tools.lib.auth_config import get_token
 from urllib.parse import urlparse,unquote
 import requests
 dongle,name=identity(route);base=ROOT/'routes'/dongle/name;base.mkdir(parents=True,exist_ok=True);os.chmod(base,0o700)
 (base/'.acquiring').write_text('Acquisition incomplete; use native remote resolution until completed')
 listing=None
 for host in route_api_hosts():
  try:listing=CommaApi(get_token(host),host=host).get('v1/route/'+dongle+'|'+name+'/files',timeout=30);break
  except APIError as e:
   if e.status_code!=404:raise
 if listing is None:raise RuntimeError('Route not found by native API hosts')
 manifest=[]
 for urls in listing.values():
  if not isinstance(urls,list):continue
  for url in urls:
   path=unquote(urlparse(url).path);parts=path.split('/');filename=parts[-1]
   if len(parts)<2 or not parts[-2].isdigit():continue
   if filename not in ['rlog.zst','rlog.bz2','rlog','qlog.zst','qlog.bz2','qlog','fcamera.hevc','ecamera.hevc','dcamera.hevc','qcamera.ts']:continue
   dest=base/(name+'--'+parts[-2])/filename;dest.parent.mkdir(exist_ok=True)
   if not dest.exists():
    tmp=dest.with_suffix(dest.suffix+'.partial')
    with requests.get(url,stream=True,timeout=(20,90)) as response:
     response.raise_for_status()
     with tmp.open('wb') as out:
      for chunk in response.iter_content(1024*1024):out.write(chunk)
    tmp.replace(dest)
   manifest.append({'path':str(dest.relative_to(base)),'bytes':dest.stat().st_size})
   print('cached',parts[-2],filename,dest.stat().st_size,flush=True)
 (base/'cache_manifest.json').write_text(json.dumps({'route':route,'native_layout':True,'files':manifest,'complete_available_files':True,'source':'native route API; signed URLs intentionally omitted'},indent=2))
 (base/'.acquiring').unlink(missing_ok=True)
 return base

def inventory():
 rows=[]
 for dongle in sorted((ROOT/'routes').iterdir()):
  if not dongle.is_dir():continue
  names=set()
  for entry in dongle.iterdir():
   match=re.match(r'(.{20})(?:--\d+)?$',entry.name)
   if match:names.add(match[1])
  for name in sorted(names):
   route=dongle.name+'/'+name;source=local_source(route)
   if source is None:continue
   segments=sorted(source.glob(name+'--*'),key=lambda p:int(p.name.rsplit('--',1)[1]))
   logs=all(any(x.glob('rlog*')) or any(x.glob('qlog*')) for x in segments)
   video=all((x/'fcamera.h264').exists() or (x/'fcamera.hevc').exists() or (x/'qcamera.ts').exists() for x in segments)
   evidence=ROOT/'routes'/dongle.name/name/'acceptance.json'
   tested=json.loads(evidence.read_text()) if evidence.exists() else None
   audit_path=ROOT/'routes'/dongle.name/name/'inventory.json';audit=json.loads(audit_path.read_text()) if audit_path.exists() else {}
   manifest_path=ROOT/'routes'/dongle.name/name/'cache_manifest.json'
   archive_path=ROOT/'routes'/dongle.name/name/'roadscore/latest.json'
   score_meta={}
   if archive_path.exists():
    session=json.loads(archive_path.read_text()).get('session','')
    if re.fullmatch(r'normal_[0-9]+',session):
     metadata=archive_path.parent/session/'metadata.json'
     if metadata.exists():score_meta=json.loads(metadata.read_text())
   rows.append({'stored_score_full_route':score_meta.get('full_route'),'stored_score_capture_timing_clean':score_meta.get('capture_timing_clean'),'route':route,'messages_verified':audit.get('required_present',False),'complete_remote_listing_cached':cache_complete(manifest_path.parent),'stored_score':archive_path.exists(),'segments':len(segments),'logs_present':logs,'camera_present':video,'navigation':('present' if audit['navigation_present'] else 'absent') if audit else ('not inspected' if not tested else tested.get('navigation','not inspected')),'normal_replay':'not tested' if not tested else tested.get('normal_replay','not tested'),'roadscore_replay':'not tested' if not tested else tested.get('roadscore_replay','not tested'),'source':str(source)})
 print(json.dumps(rows,indent=2));return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['fetch','inventory','delete']);p.add_argument('route',nargs='?');p.add_argument('--confirm-route');a=p.parse_args()
 if a.action=='fetch':fetch(a.route)
 elif a.action=='delete':
  if a.confirm_route!=a.route:raise SystemExit('Deletion requires --confirm-route with the same route ID')
  dongle,name=identity(a.route);target=ROOT/'routes'/dongle/name
  if not target.is_dir() or target.is_symlink():raise SystemExit('No owned route folder')
  shutil.rmtree(target);print('Deleted route and its owned score archive:',a.route)
 else:inventory()
