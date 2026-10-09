#!/usr/bin/env python3
"""Compile production Swift code and verify encrypted/compressed Python interop."""
from pathlib import Path
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
    subprocess.run([str(executable), str(input_file), str(output_file)], check=True)
    response = open_message(output_file.read_bytes()[4:], bytes(range(32)), "response")
    assert response["body"] == request["body"] and response["id"] == request["id"] and response["status"] == 200
    print("Python successfully decrypted and decompressed the Swift response")
    loopback = work / "loopback"
    subprocess.run([swiftc, "-parse-as-library", "-swift-version", "5", "-target", f"{arch}-apple-macosx13.0",
                    "-sdk", sdk, "-module-cache-path", str(work / "cache"), str(production / "Wire.swift"),
                    str(production / "HTTP.swift"), str(production / "GalaxyRequestTransport.swift"),
                    str(production / "LoopbackServer.swift"), str(ROOT / "tests/Loopback.swift"), "-o", str(loopback)], check=True)
    subprocess.run([str(loopback), str(production / "Resources/Web")], check=True)
