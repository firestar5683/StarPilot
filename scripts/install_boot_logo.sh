#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT_DIR/openpilot/selfdrive/assets/images/starpilot_boot.png"
TARGET="/usr/comma/bg.png"

[[ -f /AGNOS && -f "$SOURCE" && -f "$TARGET" ]] || exit 0
grep -Fq 'BACKGROUND = "/usr/comma/bg.png"' /usr/comma/magic.py || exit 0
cmp -s "$SOURCE" "$TARGET" && exit 0

mount_options="$(findmnt -n -o OPTIONS --target /)"
restore_readonly=false
case ",$mount_options," in
  *,ro,*) restore_readonly=true ;;
  *,rw,*) ;;
  *) echo "Could not determine boot image filesystem permissions" >&2; exit 1 ;;
esac

staged="$TARGET.starpilot-$$"
cleanup() {
  local result=$?
  sudo -n rm -f -- "$staged" || true
  if "$restore_readonly"; then
    sudo -n mount -o remount,ro / || return 1
  fi
  return "$result"
}
trap cleanup EXIT

if "$restore_readonly"; then
  sudo -n mount -o remount,rw /
fi
sudo -n install -m 0644 -- "$SOURCE" "$staged"
cmp -s "$SOURCE" "$staged"
sudo -n mv -f -- "$staged" "$TARGET"
sync -f "$TARGET"
