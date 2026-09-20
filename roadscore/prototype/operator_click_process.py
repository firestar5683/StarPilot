"""Explicitly attended calibration process; no import-time audio output."""
import time
RATE=48000
INTERVAL=2.4

class ClickSequence:
  """Prebuilt low-level click PCM; callback only copies memory and timestamps."""
  def __init__(self, on_click, device, count=12):
    import numpy as np
    import sounddevice as sd
    self.sd = sd
    self.on_click = on_click
    self.index = 0
    self.failed = False
    start = 2.0
    self.beats = [round((start + i * INTERVAL) * RATE) for i in range(count)]
    self.pcm = np.zeros((self.beats[-1] + RATE, 2), dtype='float32')
    t = np.arange(round(.018 * RATE)) / RATE
    click = (.07 * np.sin(2 * np.pi * 1100 * t) * np.exp(-t * 180)).astype('float32')
    for beat in self.beats:
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
    dac = time.monotonic() + float(timing.outputBufferDacTime - timing.currentTime)
    for index, beat in enumerate(self.beats):
      if self.index <= beat < self.index + frames:
        self.on_click(index, 1000 * (dac + (beat - self.index) / RATE))
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
  p=argparse.ArgumentParser();p.add_argument('--address',required=True);p.add_argument('--count',type=int,choices=[4,12],required=True);args=p.parse_args()
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
    sink=ClickSequence(lambda i,at:events.put((i,at)),device,args.count)
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
          beat,at=events.get(timeout=.1)
          print(json.dumps({'beat':beat,'server_ms':at,'timing':'host DAC estimate; includes unmeasured Bluetooth delay'}),flush=True)
        except queue.Empty:pass
    finally:sink.close()

if __name__=='__main__':main()
