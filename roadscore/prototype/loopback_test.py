"""Silent host output acceptance through the named virtual output, never a mic."""
import os
import subprocess,time,json
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf
root=Path(__file__).resolve().parents[1];blocks=[];out=root/'results/integration'
with sd.InputStream(device='BlackHole 2ch',samplerate=48000,channels=2,blocksize=480,dtype='float32',callback=lambda data,n,ti,status:blocks.append(data.copy())):
 started=time.monotonic()
 result=subprocess.run([str(root/'onroad'),'--routeid',os.environ['ROADSCORE_CURVE_ROUTE'],'--roadscore','--replay','--duration','30','--audible','--audio-device','BlackHole 2ch'],cwd=root,stdout=(out/'loopback_console.log').open('w'),stderr=subprocess.STDOUT)
 ended=time.monotonic()
wave=np.concatenate(blocks);sf.write(out/'host_loopback.wav',wave,48000,subtype='FLOAT')
(out/'loopback_capture.json').write_text(json.dumps({'exit':result.returncode,'started_host_wall':started,'ended_host_wall':ended,'frames':len(wave),'rms':float(np.sqrt(np.mean(wave*wave))),'peak':float(abs(wave).max()),'device':'BlackHole 2ch virtual loopback; no microphone or physical speaker'},indent=2))
print(result.returncode,len(wave),float(abs(wave).max()))
