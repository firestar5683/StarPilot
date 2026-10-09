#!/usr/bin/env python3
"""Read settings without changing them; print only transfer sizes/counts."""
import argparse
import base64
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from protocol import MAX_BODY, packets, seal
from proxy import INTERNAL_PARAMS, PARAMS_SNAPSHOT_LIMIT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--galaxy-url", default="http://127.0.0.1:8082")
parser.add_argument("--packet-size", type=int, default=180, choices=range(20, 513), metavar="20..512")
args = parser.parse_args()
paths = ["/api/params/all", "/assets/components/tools/device_settings_layout.json?v=settings-tier-1", "/api/params/defaults"]
old_operations = new_operations = 0
for path in paths:
    with urllib.request.urlopen(args.galaxy_url.rstrip("/") + path, timeout=10) as response:
        content_type = response.headers.get("Content-Type", "application/json")
        body = response.read(PARAMS_SNAPSHOT_LIMIT + 1)
    if len(body) > PARAMS_SNAPSHOT_LIMIT:
        raise ValueError("Snapshot exceeds bounded benchmark read limit")
    if path == "/api/params/all":
        values = json.loads(body)
        if not isinstance(values, dict):
            raise ValueError("Expected a parameter object")
        body = json.dumps({k: v for k, v in values.items() if k not in INTERNAL_PARAMS},
                          separators=(",", ":"), ensure_ascii=False).encode()
    if len(body) > MAX_BODY:
        raise ValueError("Body exceeds Bluetooth limit")
    # Public, fixed test key. Never read or print a device's real pairing key.
    envelope = {"id": "00000000-0000-0000-0000-000000000000", "session": "01" * 16,
                "counter": 1, "status": 200, "headers": {"content-type": content_type},
                "body": base64.b64encode(body).decode()}
    legacy = seal(envelope, bytes(range(32)), "response")
    compact = seal(envelope, bytes(range(32)), "response", compact_body=True)
    old_packets = len(list(packets(legacy, min(180, args.packet_size))))
    new_packets = len(list(packets(compact, args.packet_size)))
    old_operations += old_packets * 2
    new_operations += new_packets + 1
    print(f"{path}: HTTP {len(body)} B; encrypted {len(legacy)} → {len(compact)} B; "
          f"response packets {old_packets} → {new_packets}")
print(f"First settings load: {old_operations} → {new_operations} response read/ACK operations")
print("Counts exclude request writes and wait polling; this is not measured Bluetooth latency.")
