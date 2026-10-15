"""Stardust adapter for the unmodified Galaxy Bluetooth v1 implementation."""
from pathlib import Path
import sys

UPSTREAM = Path(__file__).parent / 'upstream/tools/galaxy_bluetooth/bridge'
KEY_PATH = Path('/data/galaxy-ble/pairing.json')


def upstream_module(name):
  # Upstream uses sibling imports. Only this pinned, repository-owned directory is added.
  if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))
  import importlib
  return importlib.import_module(name)


def pairing_payload(rotate=False, path=KEY_PATH):
  pairing = upstream_module('pairing')
  key = pairing.rotate_key(path) if rotate else pairing.ensure_key(path)
  return {'type': 'galaxy-bluetooth', 'version': 1, 'key': key.hex()}


def proxy_class():
  import http.cookiejar
  import threading
  from collections import OrderedDict
  import urllib.request
  proxy = upstream_module('proxy')

  class LocalOrigin(urllib.request.BaseHandler):
    def http_request(self, request):
      request.add_unredirected_header('Origin', f'http://127.0.0.1:{request.host.rsplit(":", 1)[1]}')
      return request

  class StardustProxy(proxy.GalaxyProxy):
    def __init__(self, port=8082):
      super().__init__(port)
      self.clients = OrderedDict()
      self.lock = threading.Lock()

    def handle(self, request):
      target = request.get('path', '').split('?')[0]
      # Pairing credentials are only issued over a direct LAN session. BLE is never an uplink or media transport.
      if target.startswith(('/api/companion/bluetooth', '/api/recordings/', '/api/replay/', '/api/cameras/',
                            '/api/android-auto/upload', '/api/navigation/map/tiles/')) or target in (
          '/api/companion/uplink', '/api/companion/app.apk', '/api/auth/login', '/api/auth/logout'):
        return proxy.error_response(request.get('id', ''), 501, 'This action requires Galaxy Wi-Fi or LAN.')
      # Keep preview/confirm identity stable within an authenticated BLE session; never trust phone cookies.
      session = request.get('session', '')
      with self.lock:
        local = self.clients.get(session)
        if local is None:
          local = proxy.GalaxyProxy(int(self.base.rsplit(':', 1)[1]))
          local.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), proxy.NoRedirect(), LocalOrigin(),
                                                    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
          self.clients[session] = local
          while len(self.clients) > 4:
            self.clients.popitem(last=False)
        self.clients.move_to_end(session)
      try:
        with local.opener.open(self.base + '/api/auth/session', timeout=4) as response:
          if response.status != 200:
            raise OSError('Galaxy session unavailable')
          response.read(4096)
      except OSError:
        return proxy.error_response(request.get('id', ''), 503, 'Galaxy local session unavailable.')
      request = dict(request, headers={k: v for k, v in request.get('headers', {}).items()
                                      if k.lower() in ('content-type', 'accept', 'range')})
      return local.handle(request)

  return StardustProxy


def main():
  import argparse
  import asyncio
  import logging
  server = upstream_module('server')
  server.GalaxyProxy = proxy_class()
  logging.basicConfig(level=logging.INFO)
  asyncio.run(server.serve(argparse.Namespace(key_file=str(KEY_PATH), galaxy_port=8082, adapter=None)))


if __name__ == '__main__':
  main()
