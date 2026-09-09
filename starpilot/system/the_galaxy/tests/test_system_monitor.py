from pathlib import Path
from openpilot.starpilot.system.the_galaxy.system_monitor import SystemMonitor


def proc(root, pid=123, ticks=20, start=1, command=b'/usr/bin/python\0-m\0example.worker\0--token=secret\0'):
  p=root/str(pid);p.mkdir(exist_ok=True)
  fields=['S']+['0']*23
  fields[11]=str(ticks);fields[19]=str(start);fields[21]='100'
  (p/'stat').write_text(f'{pid} (worker (test)) '+ ' '.join(fields))
  (p/'cmdline').write_bytes(command)


def fixture(root, active=100,idle=900):
  (root/'stat').write_text(f'cpu {active} 0 0 {idle} 0 0 0 0\ncpu0 {active} 0 0 {idle} 0 0 0 0\n')
  (root/'meminfo').write_text('MemTotal: 1024000 kB\nMemAvailable: 512000 kB\n')
  (root/'uptime').write_text('1234.0 0.0')


def test_cpu_cache_memory_and_secret_exclusion(tmp_path,monkeypatch):
  now=[0.0];monkeypatch.setattr('time.monotonic',lambda:now[0])
  fixture(tmp_path);proc(tmp_path)
  monitor=SystemMonitor(tmp_path);first=monitor.sample()
  assert first['cpuPercent'] is None and first['processes'][0]['cpu'] is None
  assert first['memory']['percent']==50
  assert first['processes'][0]['name']=='example.worker'
  assert 'secret' not in str(first)
  now[0]=1;assert monitor.sample() is first
  now[0]=2;fixture(tmp_path,150,1050);proc(tmp_path,ticks=20+monitor.hz)
  second=monitor.sample()
  assert second['cpuPercent']==25
  assert second['processes'][0]['cpu']==50


def test_reused_pid_has_no_inherited_cpu_or_name(tmp_path,monkeypatch):
  now=[0.0];monkeypatch.setattr('time.monotonic',lambda:now[0])
  fixture(tmp_path);proc(tmp_path);monitor=SystemMonitor(tmp_path);monitor.sample()
  now[0]=2;proc(tmp_path,start=2,command=b'/usr/bin/other\0private argument\0')
  row=monitor.sample()['processes'][0]
  assert row['cpu'] is None and row['name']=='/usr/bin/other'


def test_exiting_and_kernel_processes(tmp_path):
  fixture(tmp_path);proc(tmp_path,command=b'');(tmp_path/'456').mkdir()
  result=SystemMonitor(tmp_path).sample()
  assert result['processCount']==1
  assert result['processes'][0]['kernel']
