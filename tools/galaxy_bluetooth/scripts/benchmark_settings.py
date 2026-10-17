#!/usr/bin/env python3
"""Read settings without changing them; print only transfer sizes/counts."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from protocol import MAX_BODY, packets, seal, stream_tag, notification_packets, NOTIFICATION_WINDOW
from proxy import INTERNAL_PARAMS, PARAMS_SNAPSHOT_LIMIT, SETTINGS_UNUSED_PARAMS, FAST_SETTINGS_CATALOG_SHA256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--galaxy-url", default="http://127.0.0.1:8082")
parser.add_argument("--packet-size", type=int, default=180, choices=range(20, 513), metavar="20..512")
args = parser.parse_args()
paths = ["/api/params/all", "/assets/components/tools/device_settings_layout.json?v=settings-tier-1", "/api/params/defaults"]
old_operations = new_operations = 0
notification_count = notification_acks = 0
settings_values = None
catalog_matches = False
catalog_packets = 0
for path in paths:
    with urllib.request.urlopen(args.galaxy_url.rstrip("/") + path, timeout=10) as response:
        content_type = response.headers.get("Content-Type", "application/json")
        body = response.read(PARAMS_SNAPSHOT_LIMIT + 1)
    if len(body) > PARAMS_SNAPSHOT_LIMIT:
        raise ValueError("Snapshot exceeds bounded benchmark read limit")
    if path == "/api/params/all":
        values = json.loads(body)
        settings_values = values
        if not isinstance(values, dict):
            raise ValueError("Expected a parameter object")
        body = json.dumps({k: v for k, v in values.items() if k not in INTERNAL_PARAMS},
                          separators=(",", ":"), ensure_ascii=False).encode()
    if path.startswith("/assets/"):
        catalog_matches = hashlib.sha256(body).hexdigest() == FAST_SETTINGS_CATALOG_SHA256
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
    pushed = len(list(notification_packets(compact, stream_tag("01" * 16, 1), args.packet_size)))
    if path.startswith("/assets/"):
        catalog_packets = pushed
    credits = (pushed + NOTIFICATION_WINDOW - 1) // NOTIFICATION_WINDOW
    notification_count += pushed
    notification_acks += credits
    print(f"{path}: HTTP {len(body)} B; encrypted {len(legacy)} → {len(compact)} B; "
          f"response packets {old_packets} → {new_packets}")
print(f"First settings load: {old_operations} → {new_operations} response read/ACK operations")
print(f"Notification mode: {notification_count} pushed packets, {notification_acks} window ACKs, zero response reads")
print("Counts exclude request writes and wait polling; this is not measured Bluetooth latency.")

excluded = INTERNAL_PARAMS | SETTINGS_UNUSED_PARAMS if catalog_matches else INTERNAL_PARAMS
body = json.dumps({k: v for k, v in settings_values.items() if k not in excluded},
                  separators=(",", ":"), ensure_ascii=False).encode()
envelope["body"] = base64.b64encode(body).decode()
frame = seal(envelope, bytes(range(32)), "response", compact_body=True)
count = len(list(notification_packets(frame, stream_tag("01" * 16, 1), args.packet_size)))
optimized = count + (0 if catalog_matches else catalog_packets)
print(f"Settings-only load: {len(body)} B values, {len(frame)} B encrypted, {optimized} notification packets; "
      f"catalog {'served locally after digest verification' if catalog_matches else 'downloaded as fallback'}; no unused defaults")
