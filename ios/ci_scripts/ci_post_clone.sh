#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
python3 tests/extract_carplay_navigation.py "$test_dir/NavigationProbe.swift"
swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library "$test_dir/NavigationProbe.swift" -o "$test_dir/carplay-navigation-tests"
"$test_dir/carplay-navigation-tests"

python3 tests/extract_bluetooth_reads.py "$test_dir/BluetoothReadProbe.swift"
swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library "$test_dir/BluetoothReadProbe.swift" -o "$test_dir/bluetooth-read-tests"
"$test_dir/bluetooth-read-tests"

swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library GalaxyBluetooth/GalaxyRequestTransport.swift tests/GalaxyReadCacheRegression.swift -o "$test_dir/read-cache-tests"
"$test_dir/read-cache-tests"

swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library GalaxyBluetooth/Wire.swift GalaxyBluetooth/HTTP.swift GalaxyBluetooth/GalaxyRequestTransport.swift GalaxyBluetooth/NetworkTransport.swift GalaxyBluetooth/PrivateLANHTTP.swift tests/SecretGoodLANRegression.swift -o "$test_dir/secretgood-lan-tests"
"$test_dir/secretgood-lan-tests"
python3 tests/check_secretgood_bundle.py
swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library GalaxyBluetooth/Wire.swift GalaxyBluetooth/HTTP.swift GalaxyBluetooth/GalaxyRequestTransport.swift GalaxyBluetooth/NetworkTransport.swift GalaxyBluetooth/PrivateLANHTTP.swift GalaxyBluetooth/GalaxyAssetStore.swift tests/SecretGoodAssetsRegression.swift -o "$test_dir/secretgood-assets-tests"
"$test_dir/secretgood-assets-tests"

python3 tests/extract_legacy_link.py "$test_dir/LegacyLinkProbe.swift"
swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library "$test_dir/LegacyLinkProbe.swift" -o "$test_dir/legacy-link-tests"
"$test_dir/legacy-link-tests"

swiftc -module-cache-path "$test_dir/module-cache" -swift-version 5 -parse-as-library GalaxyBluetooth/Wire.swift GalaxyBluetooth/HTTP.swift GalaxyBluetooth/GalaxyRequestTransport.swift GalaxyBluetooth/NetworkTransport.swift GalaxyBluetooth/PrivateLANHTTP.swift GalaxyBluetooth/LoopbackServer.swift tests/LoopbackRecoveryRegression.swift -o "$test_dir/loopback-recovery-tests"
"$test_dir/loopback-recovery-tests"

if command -v node >/dev/null 2>&1; then
  node tests/ToggleSearchRegression.mjs
else
  echo "Node unavailable: run tests/ToggleSearchRegression.mjs locally for JavaScript search checks."
fi
