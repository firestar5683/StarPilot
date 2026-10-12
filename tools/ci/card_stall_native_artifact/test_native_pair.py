"""Run on native ARM CPython 3.12.13; never substitute a rebuilt companion."""
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import subprocess
import sys
import tempfile
import uuid

import pytest

PAYLOADS = [b'x', b'unchanged\x00binary', bytes(range(256)), b'z'*4096] * 32


def exact_runtime():
  assert platform.machine() == 'aarch64', platform.machine()
  assert sys.implementation.name == 'cpython' and sys.version_info[:3] == (3, 12, 13), sys.version


def child_env(root, prefix):
  env = dict(os.environ, PYTHONPATH=str(root), PYTHONNOUSERSITE='1', OPENPILOT_PREFIX=prefix)
  env.pop('CEREAL_FAKE', None)
  return env


def read_line(process, timeout=15):
  if not select.select([process.stdout], [], [], timeout)[0]:
    raise TimeoutError('native IPC subprocess did not produce its expected line')
  line = process.stdout.readline()
  if not line:
    raise RuntimeError(f'native IPC subprocess exited before its expected line: {process.poll()}')
  return line.decode().rstrip('\n')


def roots():
  return {name: Path(os.environ['ARM_CI_'+name.upper()+'_ROOT']) for name in ('baseline', 'candidate')}


def test_public_api_and_unchanged_companion():
  exact_runtime()
  results = {}
  for name, root in roots().items():
    result = subprocess.run([sys.executable, __file__, 'api'], env=child_env(root, 'api_'+uuid.uuid4().hex),
                            check=True, text=True, capture_output=True, timeout=20)
    results[name] = json.loads(result.stdout)
    assert results[name]['companion_sha256'] == os.environ['ARM_CI_COMPANION_SHA256']
    assert Path(results[name]['ipc_path']).resolve() == (root/'msgq/ipc_pyx.so').resolve()
    assert Path(results[name]['companion_path']).resolve() == (root/'msgq/visionipc/visionipc_pyx.so').resolve()
  baseline, candidate = results['baseline'], results['candidate']
  for name, methods in baseline['api'].items():
    assert set(methods) <= set(candidate['api'][name]), name
  assert {'enable_receive_timing', 'reset_receive_timing', 'take_receive_timing'} <= set(candidate['api']['SubSocket'])
  Path(os.environ['ARM_CI_PAIR_REPORT']).write_text(json.dumps(results, indent=2)+'\n')


@pytest.mark.parametrize('publisher,subscriber,timing', [
  ('baseline', 'baseline', False), ('baseline', 'candidate', False),
  ('baseline', 'candidate', True), ('candidate', 'baseline', False), ('candidate', 'candidate', True),
])
def test_interprocess_payload_equivalence(publisher, subscriber, timing):
  exact_runtime()
  packages = roots()
  with tempfile.TemporaryDirectory(prefix='msgq_armci_', dir='/dev/shm') as namespace:
    prefix = Path(namespace).name.removeprefix('msgq_')
    endpoint = 'abi_'+uuid.uuid4().hex
    processes = []
    try:
      def start(role, root, enabled):
        process = subprocess.Popen([sys.executable, __file__, role, endpoint, str(int(enabled))],
                                   env=child_env(root, prefix), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        processes.append(process)
        assert read_line(process) == 'ready'
        return process
      pub = start('publish', packages[publisher], False)
      sub = start('subscribe', packages[subscriber], timing)
      pub.stdin.write(b'go\n')
      pub.stdin.flush()
      result = json.loads(read_line(sub))
      assert result['sha256'] == hashlib.sha256(b''.join(PAYLOADS)).hexdigest()
      assert result['count'] == len(PAYLOADS)
      assert result['bytes'] == sum(map(len, PAYLOADS))
      assert sub.wait(timeout=10) == 0
      pub.stdin.write(b'done\n')
      pub.stdin.flush()
      assert pub.wait(timeout=10) == 0
    finally:
      for process in processes:
        if process.poll() is None:
          process.kill()
        process.wait(timeout=10)
        stderr = process.stderr.read().decode(errors='replace')
        if stderr:
          print(stderr, file=sys.stderr)


def child():
  exact_runtime()
  import msgq
  import msgq.ipc_pyx
  role = sys.argv[1]
  if role == 'api':
    # A missing dependency is a blocking import error, never a reason to build
    # or swap this companion, whose reviewed bytes must remain unchanged.
    import msgq.visionipc.visionipc_pyx as companion
    names = ('Context', 'SubSocket', 'PubSocket', 'Poller', 'Event', 'SocketEventHandle')
    print(json.dumps({'api': {n: sorted(x for x in dir(getattr(msgq.ipc_pyx, n)) if not x.startswith('_')) for n in names},
                      'ipc_path': msgq.ipc_pyx.__file__, 'companion_path': companion.__file__,
                      'companion_sha256': hashlib.sha256(Path(companion.__file__).read_bytes()).hexdigest(),
                      'python': sys.version, 'machine': platform.machine()}), flush=True)
    return
  endpoint, timing = sys.argv[2], bool(int(sys.argv[3]))
  if role == 'publish':
    sock = msgq.pub_sock(endpoint)
    print('ready', flush=True)
    assert input() == 'go'
    for payload in PAYLOADS:
      sock.send(payload)
    assert input() == 'done'
  elif role == 'subscribe':
    sock = msgq.sub_sock(endpoint, timeout=2000)
    if timing:
      sock.enable_receive_timing(True)
    print('ready', flush=True)
    received = [sock.receive() for _ in PAYLOADS]
    assert received == PAYLOADS
    assert sock.receive(non_blocking=True) is None
    if hasattr(sock, 'take_receive_timing'):
      records, omitted = sock.take_receive_timing()
      if timing:
        assert len(records) == 64 and omitted == len(PAYLOADS)+1-64
        assert records[-1][:4] == (len(PAYLOADS)+1, True, False, 0)
        assert all(len(r) == 12 and min(r[4:]) >= 0 for r in records)
        assert all(list(r[4::2]) == sorted(r[4::2]) and list(r[5::2]) == sorted(r[5::2]) for r in records)
      else:
        assert (records, omitted) == ((), 0)
    print(json.dumps({'count': len(received), 'bytes': sum(map(len, received)),
                      'sha256': hashlib.sha256(b''.join(received)).hexdigest()}), flush=True)
  else:
    raise ValueError(role)


if __name__ == '__main__':
  child()
