import functools, json, os, time

ENABLED = os.environ.get("STARPILOT_GPU_STARTUP_TRACE") == "1"
REPORT = None

def report(packet):
  if REPORT is not None: REPORT(packet)
  else: os.write(2, (json.dumps(packet, separators=(",", ":")) + "\n").encode())

def note(dev, event, **fields):
  if not ENABLED: return
  try:
    entries = dev.__dict__.setdefault("_startup_trace_entries", [])
    if len(entries) < 64:
      entries.append({"mono_ns": time.monotonic_ns(), "event": event, **fields})
  except Exception:
    pass

def value(dev, name, result):
  if ENABLED:
    try:
      values = dev.__dict__.setdefault("_startup_trace_values", {})
      entries = dev.__dict__.setdefault("_startup_trace_entries", [])
      if name not in values and len(entries) < 64:
        values[name] = {"mono_ns": time.monotonic_ns(), "event": name, "first": result, "last": result, "reads": 0}
        entries.append(values[name])
      if name in values:
        values[name]["last"] = result
        values[name]["reads"] += 1
    except Exception:
      pass
  return result

def emit(dev, outcome):
  if not ENABLED: return
  try:
    entries = dev.__dict__.pop("_startup_trace_entries", [])
    packet = {"kind": "starpilot_gpu_startup", "pid": os.getpid(), "device": getattr(dev, "devfmt", None),
              "outcome": outcome, "entries": entries}
    report(packet)
  except Exception:
    pass

_short_reads = 0

def short_read(address, expected, actual):
  global _short_reads
  if not ENABLED or _short_reads >= 8: return
  _short_reads += 1
  try:
    packet = {"kind": "starpilot_gpu_short_mmio", "pid": os.getpid(), "mono_ns": time.monotonic_ns(),
              "address": address, "expected": expected, "actual": actual, "sample": _short_reads}
    report(packet)
  except Exception:
    pass

def initialization(fn):
  @functools.wraps(fn)
  def call(dev, *args, **kwargs):
    note(dev, "initialization_enter")
    try:
      result = fn(dev, *args, **kwargs)
    except BaseException as exc:
      note(dev, "initialization_failed", exception=type(exc).__name__)
      emit(dev, "initialization_failed")
      raise
    note(dev, "initialization_complete")
    return result
  return call

def wait_tlb(dev, ip, inst, req, vmid, wait, read_ack):
  mask = 1 << vmid
  if not ENABLED or ip != "GC" or dev.__dict__.get("_startup_trace_gc_seen", False):
    return wait(lambda: read_ack() & mask, value=mask, msg="flush_tlb timeout")
  dev._startup_trace_gc_seen = True
  note(dev, "first_gc_request", instance=inst, request=req, vmid=vmid)
  sample = {"reads": 0, "first": None, "last": None}
  def observe():
    raw = read_ack()
    sample["reads"] += 1
    if sample["first"] is None: sample["first"] = raw
    sample["last"] = raw
    return raw & mask
  try:
    result = wait(observe, value=mask, msg="flush_tlb timeout")
  except BaseException as exc:
    note(dev, "first_gc_failure", exception=type(exc).__name__, **sample)
    emit(dev, "first_gc_failure")
    raise
  note(dev, "first_gc_acknowledged", **sample)
  emit(dev, "first_gc_acknowledged")
  return result
