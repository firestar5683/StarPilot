"""Read-only, request-driven Linux process snapshots shared by Galaxy clients."""
import os
import pwd
import shutil
import threading
import time
from pathlib import Path


class SystemMonitor:
  def __init__(self, root=Path('/proc')):
    self.root = Path(root)
    self.lock = threading.Lock()
    self.previous = {}
    self.names = {}
    self.cpu_previous = {}
    self.previous_time = None
    self.cached = None
    self.hz = os.sysconf('SC_CLK_TCK')
    self.page = os.sysconf('SC_PAGE_SIZE')

  def sample(self):
    with self.lock:
      now = time.monotonic()
      if self.cached is not None and now - self.previous_time < 1.5:
        return self.cached
      elapsed = now - self.previous_time if self.previous_time is not None else None
      cpu_now, cores = {}, []
      overall = None
      cpu_capacity = None
      for line in (self.root / 'stat').read_text().splitlines():
        values = line.split()
        if not values or not values[0].startswith('cpu'):
          continue
        values_num = [int(value) for value in values[1:9]]
        pair = (sum(values_num), values_num[3] + values_num[4])
        key = values[0]
        cpu_now[key] = pair
        old = self.cpu_previous.get(key)
        percent = None
        if old and pair[0] > old[0]:
          percent = round(max(0, min(100, 100 * (1 - (pair[1] - old[1]) / (pair[0] - old[0])))), 1)
        if key == 'cpu':
          overall = percent
          if old and pair[0] > old[0]:
            cpu_capacity = pair[0] - old[0]
        else:
          cores.append({'name': key, 'percent': percent})
      rows, ticks, names = [], {}, {}
      for path in self.root.iterdir():
        if not path.name.isdigit():
          continue
        try:
          raw = (path / 'stat').read_text()
          end = raw.rindex(')')
          fields = raw[end + 2:].split()
          identity = (int(path.name), fields[19])
          current = int(fields[11]) + int(fields[12])
          ticks[identity] = current
          info = self.names.get(identity)
          if info is None:
            args = [part for part in (path / 'cmdline').read_bytes().decode(errors='replace').split('\0') if part]
            name = raw[raw.index('(') + 1:end]
            if args:
              name = args[0]
              if 'python' in Path(name).name and len(args) > 1:
                name = args[2] if args[1] == '-m' and len(args) > 2 else (args[1] if not args[1].startswith('-') else Path(name).name)
            uid = path.stat().st_uid
            try:
              user = pwd.getpwuid(uid).pw_name
            except KeyError:
              user = str(uid)
            # Only executable/module names: never expose arguments or environment secrets.
            info = {'name': name.removeprefix('/data/openpilot/'), 'user': user, 'kernel': not args}
          names[identity] = info
          cpu = None
          if cpu_capacity and identity in self.previous and current >= self.previous[identity]:
            # Same aggregate tick window as the total, including any core hotplug.
            # 100% means all measured CPU capacity, not one fully occupied core.
            cpu = round(min(100, (current - self.previous[identity]) / cpu_capacity * 100), 1)
          rows.append({'pid': identity[0], **info, 'state': fields[0], 'cpu': cpu,
                       'memoryMiB': round(max(0, int(fields[21])) * self.page / 1048576, 1)})
        except (OSError, ValueError, IndexError):
          continue  # Process exited or is inaccessible during this snapshot.
      memory = {line.split(':')[0]: int(line.split()[1]) for line in (self.root / 'meminfo').read_text().splitlines() if ':' in line}
      total = memory['MemTotal'] / 1024
      available = memory.get('MemAvailable', memory.get('MemFree', 0)) / 1024
      disk = shutil.disk_usage('/data' if Path('/data').exists() else '/')
      self.cached = {'sampledAt': time.time(), 'sampleSeconds': round(elapsed, 2) if elapsed else None,
                     'cpuPercent': overall, 'cores': cores,
                     'memory': {'totalMiB': round(total, 1), 'usedMiB': round(total - available, 1),
                                'availableMiB': round(available, 1), 'percent': round(100 * (total - available) / total, 1)},
                     'storage': {'usedGiB': round(disk.used / 1073741824, 1), 'totalGiB': round(disk.total / 1073741824, 1)},
                     'uptimeSeconds': float((self.root / 'uptime').read_text().split()[0]),
                     'processCount': len(rows), 'processes': rows}
      self.previous, self.names, self.cpu_previous, self.previous_time = ticks, names, cpu_now, now
      return self.cached


monitor = SystemMonitor()
