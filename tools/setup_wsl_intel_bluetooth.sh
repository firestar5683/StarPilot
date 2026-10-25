#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 || -z "${SUDO_USER:-}" || ! -x /usr/bin/wslinfo ]]; then
  echo 'Run this from Ubuntu WSL with sudo.' >&2
  exit 1
fi

source /etc/os-release
if [[ $ID != ubuntu || $VERSION_ID != 24.04 ]]; then
  echo 'This setup supports Ubuntu 24.04 under WSL.' >&2
  exit 1
fi
if [[ ! $SUDO_USER =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo 'Unsupported Linux username for Bluetooth service permissions.' >&2
  exit 1
fi

apt-get update
apt-get install -y bluez linux-firmware-intel-wireless zstd usbutils

install -d -m 0755 /usr/local/libexec
cat > /usr/local/libexec/openpilot-wsl-bluetooth-firmware <<'SH'
#!/bin/sh
set -eu
source_dir=/usr/lib/firmware/intel
shared_dir=/mnt/wsl/firmware/intel
mkdir -p "$shared_dir"
for file in ibt-0040-0041.sfi ibt-0040-0041.ddc; do
  zstd -dc "$source_dir/$file.zst" > "$shared_dir/$file"
done
printf '%s' /mnt/wsl/firmware > /sys/module/firmware_class/parameters/path
SH
chmod 0755 /usr/local/libexec/openpilot-wsl-bluetooth-firmware

cat > /etc/systemd/system/openpilot-wsl-bluetooth-firmware.service <<'UNIT'
[Unit]
Description=Expose Intel Bluetooth firmware to the WSL kernel
ConditionPathExists=/usr/lib/firmware/intel/ibt-0040-0041.sfi.zst
After=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/libexec/openpilot-wsl-bluetooth-firmware

[Install]
WantedBy=multi-user.target
UNIT

sudoers_file=$(mktemp)
trap 'rm -f "$sudoers_file"' EXIT
printf '%s\n' "$SUDO_USER ALL=(root) NOPASSWD: /usr/bin/systemctl start bluetooth.service, /usr/bin/systemctl stop bluetooth.service, /usr/bin/btmgmt --index 0 class *" > "$sudoers_file"
visudo -cf "$sudoers_file"
install -m 0440 "$sudoers_file" /etc/sudoers.d/starpilot-bluetooth
systemctl daemon-reload
systemctl enable --now openpilot-wsl-bluetooth-firmware.service
