#!/usr/bin/env python3
"""Compile production Swift code and verify encrypted/compressed Python interop."""
from pathlib import Path
import base64
import json
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from protocol import open_message, seal

if platform.system() != "Darwin":
    raise SystemExit("The Swift/CryptoKit interoperability check requires macOS and Xcode.")

swiftc = subprocess.check_output(["/usr/bin/xcrun", "--find", "swiftc"], text=True).strip()
sdk = subprocess.check_output(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
arch = "arm64" if platform.machine() == "arm64" else "x86_64"
with tempfile.TemporaryDirectory(prefix="galaxy-interop-") as folder:
    work = Path(folder)
    executable = work / "interop"
    production = ROOT / "ios/GalaxyBluetooth"
    subprocess.run([swiftc, "-parse-as-library", "-swift-version", "5", "-target", f"{arch}-apple-macosx13.0",
                    "-sdk", sdk, "-module-cache-path", str(work / "cache"), str(production / "Wire.swift"),
                    str(production / "HTTP.swift"), str(ROOT / "tests/Interop.swift"), "-o", str(executable)], check=True)
    request = {"id": "test-interop", "session": "01" * 16, "counter": 1, "path": "/api/params", "method": "PUT",
               "headers": {}, "body": "settings" * 4096}
    input_file, output_file = work / "request.bin", work / "response.bin"
    input_file.write_bytes(seal(request, bytes(range(32)), "request"))
    raw = json.dumps([{"repeated_setting": n, "label": "Galaxy ✨"} for n in range(1000)]).encode()
    compact_file, body_file = work / "compact.bin", work / "body.bin"
    body_file.write_bytes(raw)
    compact_file.write_bytes(seal({"id": "compact", "session": "01" * 16, "counter": 2,
                                  "status": 200, "headers": {}, "body": base64.b64encode(raw).decode()},
                                 bytes(range(32)), "response", compact_body=True))
    subprocess.run([str(executable), str(input_file), str(output_file), str(compact_file), str(body_file)], check=True)
    response = open_message(output_file.read_bytes()[4:], bytes(range(32)), "response")
    assert response["body"] == request["body"] and response["id"] == request["id"] and response["status"] == 200
    print("Python successfully decrypted and decompressed the Swift response")
    loopback = work / "loopback"
    subprocess.run([swiftc, "-parse-as-library", "-swift-version", "5", "-target", f"{arch}-apple-macosx13.0",
                    "-sdk", sdk, "-module-cache-path", str(work / "cache"), str(production / "Wire.swift"),
                    str(production / "HTTP.swift"), str(production / "GalaxyRequestTransport.swift"),
                    str(production / "LoopbackServer.swift"), str(ROOT / "tests/Loopback.swift"), "-o", str(loopback)], check=True)
    subprocess.run([str(loopback), str(production / "Resources/Web")], check=True)
    cache = work / "read-cache"
    subprocess.run([swiftc, "-parse-as-library", "-swift-version", "5", "-target", f"{arch}-apple-macosx13.0",
                    "-sdk", sdk, "-module-cache-path", str(work / "cache"), str(production / "Wire.swift"),
                    str(production / "GalaxyRequestTransport.swift"), str(ROOT / "tests/ReadCache.swift"),
                    "-o", str(cache)], check=True)
    subprocess.run([str(cache)], check=True)
