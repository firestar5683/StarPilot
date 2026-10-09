#!/usr/bin/env python3
"""Compile Android's production Java wire code and exchange frames with Python."""
import argparse
import base64
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from protocol import seal, open_message, notification_packets, stream_tag
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--java-home", type=Path, required=True)
parser.add_argument("--json-jar", type=Path, required=True, help="org.json's JVM jar (Android provides its own JSON implementation)")
args = parser.parse_args()
key = bytes(range(32))
with tempfile.TemporaryDirectory(prefix="galaxy-android-interop-") as folder:
    folder = Path(folder)
    java = ROOT / "android/app/src/main/java/link/firestar/galaxybt"
    subprocess.run([str(args.java_home / "bin/javac"), "-cp", str(args.json_jar.resolve()), "-d", str(folder),
                    str(java / "BridgeWire.java"), str(java / "RequestPolicy.java"), str(ROOT / "tests/AndroidInterop.java")], check=True)
    request = {"id": "test-android", "session": "01" * 16, "counter": 1, "path": "/api/params", "method": "PUT",
               "headers": {"content-type": "application/json"}, "body": base64.b64encode(b'{"key":"Metric","value":true}').decode()}
    for compact in (False, True):
        for body in (json.dumps([{"key": f"setting-{i}", "label": "Galaxy ✨"} for i in range(1000)]).encode(), bytes(range(256)) * 100):
            input_file, output_file, response_file = folder / "request", folder / "output", folder / "response"
            body_file, notifications_file, acks_file = folder / "body", folder / "notifications", folder / "acks"
            input_file.write_bytes(seal(request, key, "request"))
            frame = seal({"id": "response", "session": "01" * 16, "counter": 2, "status": 200, "headers": {},
                          "body": base64.b64encode(body).decode()}, key, "response", compact_body=compact)
            response_file.write_bytes(frame); body_file.write_bytes(body)
            tag = stream_tag("01" * 16, 2)
            for size in (20, 180, 244, 512):
                packets = list(notification_packets(frame, tag, size))
                notifications_file.write_bytes(b"".join(struct.pack(">I", len(p)) + p for p in packets))
                subprocess.run([str(args.java_home / "bin/java"), "-cp", str(folder) + ":" + str(args.json_jar.resolve()),
                                "link.firestar.galaxybt.AndroidInterop", *map(str, (input_file, output_file, response_file, body_file, notifications_file, acks_file))], check=True, stdout=subprocess.DEVNULL)
                assert open_message(output_file.read_bytes()[4:], key, "request") == request
                expected = [min(start + 8, len(packets)) - 1 for start in range(0, len(packets), 8)]
                assert acks_file.read_bytes() == b"".join(b"\x04" + tag + struct.pack(">I", n) for n in expected)
    print("Android/Python production interop passed: JSON/binary, legacy/compact, ATT sizes 20/180/244/512, tagged window ACKs, tamper/direction/bounds and request policy")
