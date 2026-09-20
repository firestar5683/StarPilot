"""Explicitly attended calibration process; no import-time audio output."""
import time
RATE=48000
from operator_output import COUNT, COUNT_IN, REFINE_COUNT, TEST_COUNT, INTERVAL, MARKER_OFFSETS

class ClickSequence:
  """Prebuilt low-level click PCM; callback only copies memory and timestamps."""
  def __init__(self, on_click, device, count=COUNT, on_timing=None):
    import numpy as np
    import sounddevice as sd
    self.sd = sd
    self.on_click = on_click
    self.on_timing = on_timing
    self.index = 0
    self.failed = False
    start = 2.0
    if count not in (TEST_COUNT,COUNT,REFINE_COUNT):raise ValueError('Unsupported calibration sequence')
    offsets=[start+i*INTERVAL for i in range(COUNT_IN if count==COUNT else count)]
    if count==COUNT:offsets+=list(MARKER_OFFSETS)
    self.beats = [round(at * RATE) for at in offsets]
    self.pcm = np.zeros((self.beats[-1] + RATE, 2), dtype='float32')
    t = np.arange(round(.018 * RATE)) / RATE
    downbeat = (.07 * np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 180)).astype('float32')
    beat_click = (.0455 * np.sin(2 * np.pi * 880 * t) * np.exp(-t * 180)).astype('float32')
    tone_t = np.arange(round(.045 * RATE)) / RATE
    envelope = np.sin(np.pi * np.arange(len(tone_t)) / len(tone_t)) ** 2
    marker = np.zeros(round(.13 * RATE), dtype='float32')
    marker[:len(tone_t)] = .07 * np.sin(2 * np.pi * 880 * tone_t) * envelope
    second = round(.08 * RATE)
    marker[second:second + len(tone_t)] = .07 * np.sin(2 * np.pi * 1760 * tone_t) * envelope
    for index,beat in enumerate(self.beats):
      click = marker if count == COUNT and index >= COUNT_IN else downbeat if index % 4 == 0 else beat_click
      self.pcm[beat:beat + len(click)] = click[:, None]
    self.stream = sd.OutputStream(device=device, samplerate=RATE, channels=2, dtype='float32', blocksize=480,
                                  callback=self.callback)

  def callback(self, out, frames, timing, status):
    if status:
      self.failed = True
    out.fill(0)
    end = min(self.index + frames, len(self.pcm))
    if end > self.index:
      out[:end-self.index] = self.pcm[self.index:end]
    # PortAudio host clock mapped to the local monotonic clock at callback time.
    callback_wall=time.monotonic()
    dac_lead=float(timing.outputBufferDacTime-timing.currentTime)
    dac=callback_wall+dac_lead
    for index, beat in enumerate(self.beats):
      if self.index <= beat < self.index + frames:
        offset=(beat-self.index)/RATE
        projected=dac+offset
        self.on_click(index,1000*projected)
        if self.on_timing is not None:
          self.on_timing(dict(beat=index,server_ms=1000*projected,callback_wall=callback_wall,
                             sample_offset_seconds=offset,dac_lead_seconds=dac_lead,dac_projected_wall=projected,
                             portaudio_current_time=float(timing.currentTime),portaudio_dac_time=float(timing.outputBufferDacTime),
                             stream_settings=dict(rate=RATE,channels=2,blocksize=480,callback_frames=frames,dtype='float32')))
    self.index += frames

  def start(self):
    self.stream.start()

  def close(self):
    self.stream.stop()
    self.stream.close()


def main():
  import argparse,json,queue,tempfile,os
  from pathlib import Path
  from bluetooth_output import prepare_output,select_device
  from operator_output import real_offroad,selected_output
  p=argparse.ArgumentParser();p.add_argument('--address',required=True);p.add_argument('--count',type=int,choices=[TEST_COUNT,COUNT,REFINE_COUNT],required=True);args=p.parse_args()
  output=selected_output()
  if not real_offroad() or not output or not output['connected'] or output['address']!=args.address:
    raise RuntimeError('Park and reconnect the selected Bluetooth speaker before calibration')
  with tempfile.TemporaryDirectory(prefix='calibration-',dir='/data/roadscore/generated') as folder:
    metadata=prepare_output(folder)
    if metadata.get('address')!=args.address:raise RuntimeError('Bluetooth output changed')
    import sounddevice as sd
    device=select_device(sd.query_devices(),metadata)
    sd.check_output_settings(device=device,channels=2,dtype='float32',samplerate=RATE)
    events=queue.SimpleQueue()
    sink=ClickSequence(lambda *_:None,device,args.count,on_timing=events.put)
    parent=os.getppid();last_check=0.
    sink.start()
    try:
      while sink.index<len(sink.pcm):
        if os.getppid()!=parent:raise RuntimeError('Calibration owner exited')
        if time.monotonic()-last_check>=1:
          last_check=time.monotonic()
          if not real_offroad():raise RuntimeError('Calibration ended because the device is no longer parked')
        if sink.failed:raise RuntimeError('Audio callback timing failed; retry calibration')
        try:
          event=events.get(timeout=.1)
          print(json.dumps({**event,'timing':'host DAC projection; residual includes human timing bias and unmeasured output delay'}),flush=True)
        except queue.Empty:pass
    finally:sink.close()

if __name__=='__main__':
  import json,sys,traceback
  try:main()
  except Exception as error:
    print(json.dumps({'error':f'{type(error).__name__}: {error}'[:1500]}),flush=True)
    traceback.print_exc();sys.exit(1)
