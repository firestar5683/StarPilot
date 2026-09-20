"""Atomically relay current native status without waiting on replay supervision."""
import json
import threading


class StatusRelay:
  def __init__(self, source, destination, interval=.05):
    self.source,self.destination,self.interval=source,destination,interval
    self.stop=threading.Event()
    self.thread=threading.Thread(target=self.run,daemon=True)

  def start(self):
    self.thread.start()

  def run(self):
    previous=None
    while not self.stop.is_set():
      try:
        payload=self.source.read_bytes()
        if payload!=previous:
          json.loads(payload)
          temporary=self.destination.with_suffix('.relay.tmp')
          temporary.write_bytes(payload);temporary.replace(self.destination)
          previous=payload
      except (OSError,ValueError):pass
      self.stop.wait(self.interval)

  def close(self):
    self.stop.set();self.thread.join(timeout=1)
