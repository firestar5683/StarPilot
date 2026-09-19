"""Post-download readability and camera header audit; no runtime score inputs."""
import hashlib,json,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from route_library import ROOT
ffprobe='/opt/homebrew/bin/ffprobe' if Path('/opt/homebrew/bin/ffprobe').exists() else 'ffprobe'
def check(item):
 base,entry=item;p=base/entry['path'];row={'path':entry['path'],'bytes':p.stat().st_size,'size_matches':p.stat().st_size==entry['bytes']}
 h=hashlib.sha256()
 with p.open('rb') as f:
  while data:=f.read(4*1024*1024):h.update(data)
 row['sha256']=h.hexdigest()
 if p.suffix in ['.hevc','.ts']:
  result=subprocess.run([ffprobe,'-v','error','-show_entries','stream=codec_name,width,height','-of','json',str(p)],capture_output=True,text=True,timeout=30)
  row['camera_readable']=result.returncode==0 and bool(json.loads(result.stdout).get('streams'));row['streams']=json.loads(result.stdout).get('streams',[])
 return row
for manifest in sorted((ROOT/'routes').glob('*/*/cache_manifest.json')):
 data=json.loads(manifest.read_text())
 with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,[(manifest.parent,e) for e in data['files']]))
 (manifest.parent/'verification.json').write_text(json.dumps({'route':data['route'],'all_sizes_match':all(x['size_matches'] for x in rows),'all_cameras_readable':all(x.get('camera_readable',True) for x in rows),'files':rows},indent=2))
 print(data['route'],len(rows),'files verified',flush=True)
