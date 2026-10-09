#!/usr/bin/env python3
"""Verify the APK contains the shared Galaxy bundle and only the Android HTML shim change."""
import argparse
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("apk", type=Path)
args = parser.parse_args()
web = root / "ios/GalaxyBluetooth/Resources/Web"
checked = 0
with zipfile.ZipFile(args.apk) as apk:
    assert apk.testzip() is None
    for path in web.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(web)
        expected = path.read_bytes()
        if relative.as_posix() == "assets/mobile/index.html":
            expected = expected.replace(b"<head>", b'<head>\n  <script src="/native-bridge.js"></script>')
        assert apk.read("assets/Web/" + relative.as_posix()) == expected, relative
        checked += 1
    assert apk.read("assets/native-bridge.js") == (root / "android/app/src/main/assets/native-bridge.js").read_bytes()
    assert not any(name.endswith((".jks", ".keystore", "pairing.json", "local.properties")) for name in apk.namelist())
print(f"APK verified: {checked} shared Galaxy files, Android shim, no bundled pairing/build keys; SHA-256 {hashlib.sha256(args.apk.read_bytes()).hexdigest()}")
