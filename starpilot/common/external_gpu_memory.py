"""Optional physical VRAM accounting; no hardware reads or allocation changes."""
import time


def allocated_vram(device):
  """Return used/reserved and physical total bytes from the opened AMD driver.

  Physical free pools exclude firmware reservations. Cached buffers and page
  tables remain allocated, so they count as used. Never use process-wide tensor
  counters (which also include onboard devices) as Chestnut usage.
  """
  try:
    driver = device.iface.dev_impl
    total = driver.vram_size
    pools = (driver.mm.boot_allocator, driver.mm.ptable_allocator, driver.mm.pa_allocator)
    if type(total) is not int or total <= 0:
      return None
    free = 0
    capacity = 0
    for pool in pools:
      if type(pool.size) is not int or pool.size < 0:
        return None
      blocks = tuple(pool.blocks.values())
      if any(type(b[0]) is not int or b[0] < 0 or type(b[3]) is not bool for b in blocks):
        return None
      if sum(b[0] for b in blocks) != pool.size:
        return None
      capacity += pool.size
      free += sum(b[0] for b in blocks if b[3])
    if not 0 <= free <= capacity <= total:
      return None
    return total - free, total
  except Exception:
    # Driver revisions/racing snapshots must not break model execution.
    return None


def external_gpu_memory(sm, now_ns=None, *, envelope_max_age_ns=1_000_000_000):
  """Return ((used, total), remaining ms) or (None, 0), independently of temp."""
  now_ns = time.monotonic_ns() if now_ns is None else now_ns
  try:
    remaining = []
    for service in ("deviceState", "chestnutState"):
      if not sm.valid.get(service, False) or not sm.alive.get(service, False):
        return None, 0
      age = now_ns - sm.logMonoTime[service]
      if not 0 <= age <= envelope_max_age_ns:
        return None, 0
      remaining.append(envelope_max_age_ns - age)
    if not sm["deviceState"].chestnutPresent:
      return None, 0
    state = sm["chestnutState"]
    age = now_ns - state.memorySampleMonoTime
    if state.memorySampleMonoTime <= 0 or not 0 <= age <= 15_000_000_000:
      return None, 0
    remaining.append(15_000_000_000 - age)
    used, total = state.memoryUsedBytes, state.memoryTotalBytes
    if not 0 <= used <= total or total <= 0:
      return None, 0
    return (used, total), min(remaining) // 1_000_000
  except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
    return None, 0
