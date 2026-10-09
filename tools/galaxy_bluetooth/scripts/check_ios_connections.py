#!/usr/bin/env python3
"""Test production iPhone routing and GitHub update handling on macOS.
Optional argument: a comma private IPv4 address for read-only LAN verification.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
root = Path(__file__).resolve().parents[1]
production = root / 'ios/GalaxyBluetooth'
with tempfile.TemporaryDirectory(prefix='galaxy-connections-') as folder:
    target = Path(folder)
    files = ['Wire.swift', 'GalaxyRequestTransport.swift', 'NetworkTransport.swift', 'GalaxyAssetStore.swift']
    subprocess.run(['xcrun', 'swiftc', '-parse-as-library', '-swift-version', '5', '-module-cache-path', str(target / 'cache'),
                    *[str(production / file) for file in files], str(root / 'tests/Connections.swift'), '-o', str(target / 'test')], check=True)
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            try:
                if self.path == '/redirect':
                    self.send_response(302); self.send_header('Location', '/should-not-follow'); self.end_headers(); return
                if self.path == '/slow': time.sleep(0.3)
                self.send_response(200)
                if self.path != '/unknown-size': self.send_header('Content-Length', '2048' if self.path == '/oversize' else '2')
                self.end_headers()
                self.wfile.write(b'x' * 2048 if self.path in ('/oversize', '/unknown-size') else b'ok')
            except (BrokenPipeError, ConnectionResetError): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        env = dict(os.environ, GALAXY_HTTP_FIXTURE=f'http://127.0.0.1:{server.server_port}')
        subprocess.run([str(target / 'test'), *sys.argv[1:]], check=True, env=env)
    finally:
        server.shutdown(); server.server_close()
