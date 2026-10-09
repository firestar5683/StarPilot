#!/usr/bin/env bash
# Called in the background by /data/continue.sh; systemd owns the bridge.
# /run is writable and recreated on boot, unlike the comma system partition.
unit=/data/openpilot/tools/galaxy_bluetooth/bridge/galaxy-ble-fork.service
if [ ! -r "$unit" ]; then
  echo "Galaxy BLE startup skipped: service file missing"
  exit 0
fi
timeout 20s sudo -n systemctl link --runtime "$unit" || exit 1
timeout 20s sudo -n systemctl start galaxy-ble-fork.service
