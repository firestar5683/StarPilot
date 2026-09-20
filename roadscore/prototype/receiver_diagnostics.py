"""Bounded terminal diagnostics for a failed RoadScore receiver."""
from pathlib import Path
import re


def receiver_failure(error, log_path):
  if getattr(error, 'component', None) != 'receiver':
    return error
  path=Path(log_path)
  try:
    with path.open('rb') as handle:
      handle.seek(0,2);size=handle.tell();handle.seek(max(0,size-8192))
      text=handle.read(8192).decode('utf-8',errors='replace')
    text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text=''.join(c for c in text if c in '\n\t' or ord(c)>=32)
    text=re.sub(r'(?i)(bearer\s+)[^\s]+', r'\1[redacted]', text)
    text=re.sub(r'''(?ix)((?:token|password|secret|authorization|api[_-]?key)["']?\s*[:=]\s*["']?)[^\s,"'}]+''',r'\1[redacted]',text)
    text=re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@',r'\1[redacted]@',text)
    excerpt='\n'.join(text.strip().splitlines()[-12:])[-1800:]
  except OSError:
    excerpt='Receiver log is unavailable.'
  error.args=(f'RoadScore receiver exited with status {getattr(error,"code","unknown")}.\n'
              f'Log: {path}\n{excerpt or "Receiver log is empty."}',)
  return error
