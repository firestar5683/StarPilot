#!/usr/bin/env bash
# Run on the comma over SSH. Stages a fresh checkout, preserves the old tree,
# then reboots into this test branch. Never deletes Params or pairing keys.
set -euo pipefail

repo_url=https://github.com/natehuby76/StarPilotBT.git
test_branch=secretgood-phone-test
installed=/data/openpilot

parked() {
  [[ -f /AGNOS && -d "$installed/.git" && "$(cat /data/params/d/IsOffroad 2>/dev/null)" == 1 ]]
}

if ! parked; then
  echo 'Run this on the comma while its UI is Offroad. Nothing was changed.' >&2
  exit 1
fi
sudo -n true
staged=$(mktemp -d /data/secretgood-phone-test.XXXXXX)
backup="/data/openpilot-before-secretgood-$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -e "$backup" ]]; then
  echo 'Backup path already exists. Nothing was changed.' >&2
  exit 1
fi
trap 'echo "Installation stopped. Staged checkout: $staged. Previous checkout, if moved: $backup" >&2' ERR

echo 'Downloading SecretGood phone test branch. Current installation stays in place until verification finishes.'
git clone --depth 32 --single-branch --branch "$test_branch" "$repo_url" "$staged"
[[ -f "$staged/prebuilt" && -x "$staged/launch_openpilot.sh" && -x "$staged/launch_chffrplus.sh" ]]
[[ -f "$staged/openpilot/starpilot/galaxy/web/index.html" ]]
[[ -f "$staged/openpilot/starpilot/galaxy_bluetooth/bridge/server.py" ]]
[[ "$(git -C "$staged" remote get-url origin)" == "$repo_url" ]]
[[ "$(git -C "$staged" branch --show-current)" == "$test_branch" ]]
git -C "$staged" merge-base --is-ancestor 01fd37fa7509174d71a626f66fa5567b4603b00e HEAD
# SecretGood's unchanged launch script handles its required AGNOS version.
# Do not attempt to rewrite or migrate the installed Params from this script.
if ! parked; then
  echo 'Comma is no longer Offroad. Current installation was not changed.' >&2
  exit 1
fi
mv "$installed" "$backup"
if ! mv "$staged" "$installed"; then
  mv "$backup" "$installed"
  echo 'Activation failed; the previous installation was restored.' >&2
  exit 1
fi
sync
echo "Installed $repo_url branch $test_branch. Previous checkout: $backup"
echo 'Rebooting. First phone bridge setup needs internet. Pair through Settings > Bluetooth.'
sudo -n reboot
