"""Resume private ACE asset staging from the preserved Desktop baseline. No generation."""
import argparse, os, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'prototype'))
from device_target import device_target
from route_library import identity
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path.home()/'Desktop/RoadScore');p.add_argument('--device',default=device_target());p.add_argument('--known-route',help='Optional already-used regression route; not a judging batch');a=p.parse_args()
if not a.device or a.device.startswith('-') or any(c.isspace() for c in a.device):p.error('Invalid SSH destination')
source=a.source.resolve();base=source/'experiments/ace_chestnut_20260916'
for name in ['weights','vae_weights','profiles']:
 if not (base/name).is_dir():raise SystemExit('Missing preserved asset directory: '+str(base/name))
def sync(src,dst,extra=()):
 subprocess.run(['rsync','-a','--partial','--timeout=45','-e','ssh -o BatchMode=yes -o ConnectTimeout=8',*extra,str(src),a.device+':'+dst],check=True)
subprocess.run(['ssh',a.device,'mkdir -p /data/roadscore/experiments/ace_chestnut_20260916 /data/roadscore/assets'],check=True)
for name in ['weights','vae_weights','profiles']:
 sync(base/name,'/data/roadscore/experiments/ace_chestnut_20260916/')
fixture=source/'results/ace_stability_20260916/cases/shape_56/native_0/latents.npy'
if fixture.is_file():sync(fixture,'/data/roadscore/assets/decoder_repro_latents.npy')
if a.known_route:
 dongle,route=identity(a.known_route);folder=source/'routes'/dongle/route
 if not folder.is_dir():raise SystemExit('Known local route unavailable')
 subprocess.run(['ssh',a.device,'mkdir -p /data/roadscore/routes/'+dongle],check=True)
 sync(folder,'/data/roadscore/routes/'+dongle+'/',('--exclude=roadscore/','--exclude=acceptance.json','--exclude=inventory.json','--exclude=verification.json','--exclude=*.partial','--exclude=.acquiring'))
print('Transfer complete. This does not certify hardware generation or replay.')
