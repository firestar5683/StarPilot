"""Bounded read-only event inventory. Does not open a GPU or audio stream."""
import json, os, platform, subprocess, time
from pathlib import Path

def command(args):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=5)
  return {'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except (OSError,subprocess.TimeoutExpired) as e:return {'error':str(e)}

def read(path):
 try:return Path(path).read_text().strip()
 except OSError:return None

if __name__=='__main__':
 root=Path(__file__).resolve().parents[1]
 result={'wall':time.time(),'platform':platform.platform(),'agnos':read('/VERSION'),
 'tici':Path('/TICI').exists(),'tizi':Path('/TIZI').exists(),'soc':read('/sys/devices/soc0/machine'),
 'cpu_online':read('/sys/devices/system/cpu/online'),'memory':read('/proc/meminfo'),
 'cpu_policies':{str(p):read(p) for p in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_*') if p.is_file()},
 'thermal':{str(p):read(p) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')},
 'session_muted':(root/'.session-muted').exists()}
 for key,args in {'usb':['lsusb'],'storage':['df','-h','/data','/home','/tmp'],
  'revision':['git','-C','/data/openpilot','rev-parse','HEAD'],
  'network':['ip','-brief','address'],'bluetooth':['bluetoothctl','show'],
  'alsa':['aplay','-l'],'pulse_sinks':['pactl','list','short','sinks']}.items():result[key]=command(args)
 print(json.dumps(result,indent=2))
