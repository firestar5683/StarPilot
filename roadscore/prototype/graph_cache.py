"""Opt-in local trusted TinyJit snapshot experiment. Never accepts route-supplied files."""
import hashlib,json,os,pickle,subprocess,time
from pathlib import Path
ROOT=Path('/data/roadscore/generated');MODEL=Path('/data/sa3-feasibility/native')
def signature():
 code=Path('/data/sa3-feasibility/native_sa3.py').read_bytes()
 rev=subprocess.check_output(['git','-C','/data/openpilot/tinygrad_repo','rev-parse','HEAD']).decode().strip()
 weights=[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(MODEL.glob('*.npy'))]
 return hashlib.sha256(code+json.dumps([rev,weights,os.environ.get('DEV'),os.environ.get('ROADSCORE_WINDOW_FRAMES','324')]).encode()).hexdigest()
def save(bundle):
 t=time.monotonic();tmp=ROOT/'trusted_graph.tmp';path=ROOT/'trusted_graph.pkl'
 with tmp.open('wb') as f:os.chmod(tmp,0o600);pickle.dump(bundle,f,protocol=5)
 tmp.replace(path);(ROOT/'trusted_graph.json').write_text(json.dumps({'signature':signature(),'bytes':path.stat().st_size,'save_seconds':time.monotonic()-t},indent=2))
def load():
 meta=json.loads((ROOT/'trusted_graph.json').read_text());assert meta['signature']==signature(),'Graph snapshot incompatible'
 path=ROOT/'trusted_graph.pkl';assert path.stat().st_uid==os.getuid() and not path.is_symlink(),'Snapshot must be locally owned'
 from tinygrad.uop.ops import UOp,UOpMetaClass,Ops,buffers
 import itertools
 # This tinygrad revision does not advance the allocation counter on unpickle.
 # Load before allocating inputs, then reserve all restored buffer identifiers.
 assert not buffers,'Restore must precede tensor allocation to prevent ID aliases'
 with path.open('rb') as f:bundle=pickle.load(f)
 UOp.unique_num=itertools.count(max([key[2].slot for key in UOpMetaClass.ucache if key[0] is Ops.BUFFER]+[-1])+1)
 return bundle

def stage_warm(meta):
 import shutil
 for kind,ext in [('wav','wav'),('latents','npy')]:shutil.copy(meta[kind],ROOT/('trusted_warm.'+ext))
 record={**meta,'source_hash':hashlib.sha256(Path(meta['anchor_latents']).read_bytes()).hexdigest()}
 (ROOT/'trusted_warm.json').write_text(json.dumps(record))
def restore_warm(identity):
 import shutil
 record=json.loads((ROOT/'trusted_warm.json').read_text());assert record['identity']==identity,'Cached startup identity mismatch'
 assert record['source_hash']==hashlib.sha256(Path(record['anchor_latents']).read_bytes()).hexdigest(),'Cached startup source changed'
 for kind,ext in [('wav','wav'),('latents','npy')]:
  path=ROOT/('job_-1.'+ext);shutil.copy(ROOT/('trusted_warm.'+ext),path);record[kind]=str(path)
 record['reused_startup_audio']=True;return record
