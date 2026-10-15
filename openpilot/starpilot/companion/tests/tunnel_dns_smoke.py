"""Real ARM64 mapped-DNS smoke test; run only inside a disposable container."""

import json
import socket
import struct
import subprocess
import time
import pathlib


def main():
  config = {
    'tunnel': {'name': 'spuplink0', 'mtu': 1500, 'ipv4': '198.18.0.1'},
    'socks5': {'address': '172.31.254.10', 'port': 1080, 'udp': 'udp', 'username': 'a' * 32, 'password': 'b' * 32},
    'mapdns': {'address': '198.18.0.2', 'port': 53, 'network': '198.19.0.0', 'netmask': '255.255.0.0', 'cache-size': 10000},
  }
  pathlib.Path('/tmp/tunnel.json').write_text(json.dumps(config))
  p = subprocess.Popen(['/b/hev-socks5-tunnel_linux_arm64', '/tmp/tunnel.json'])
  try:
    for _ in range(50):
      if pathlib.Path('/sys/class/net/spuplink0').exists():
        break
      if p.poll() is not None:
        raise RuntimeError('tunnel process exited')
      time.sleep(0.1)
    subprocess.run(['ip', 'link', 'set', 'spuplink0', 'up'], check=True)
    subprocess.run(['ip', 'route', 'add', '198.18.0.0/15', 'dev', 'spuplink0'], check=True)
    for kind in (1, 28):
      question = b''.join(bytes([len(v)]) + v for v in [b'api', b'mapbox', b'com']) + b'\0' + struct.pack('!HH', kind, 1)
      wire = struct.pack('!HHHHHH', 123, 0x100, 1, 0, 0, 0) + question
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        sock.sendto(wire, ('198.18.0.2', 53))
        result = sock.recv(4096)
      header = struct.unpack('!HHHHHH', result[:12])
      assert header[1] & 15 == 0, header
      if kind == 1:
        assert header[3] == 1
        assert result[-4:-2] == bytes([198, 19]), result
      else:
        assert header[3] == 0, header
      print('Mapped DNS', 'A' if kind == 1 else 'AAAA', 'PASS', header)
  finally:
    p.terminate()
    p.wait(timeout=5)


if __name__ == '__main__':
  main()
