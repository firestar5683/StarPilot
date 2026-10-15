#!/usr/bin/env bash
set -euo pipefail
COMPANION_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export COMPANION_KEYSTORE="${COMPANION_KEYSTORE:-$HOME/.starpilot/companion.jks}"
if [[ -z "${JAVA_HOME:-}" && -d '/Applications/Android Studio.app/Contents/jbr/Contents/Home' ]]; then
  export JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home'
fi
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
if [[ ! -f "$COMPANION_KEYSTORE" ]]; then
  echo 'Missing release signing key. Follow README.md to create it once; never commit it.' >&2
  exit 1
fi
if [[ -z "${COMPANION_KEY_PASSWORD:-}" ]]; then
  COMPANION_PASSWORD_FILE="${COMPANION_PASSWORD_FILE:-$HOME/.starpilot/companion-signing-password}"
  export COMPANION_KEY_PASSWORD="$(cat "$COMPANION_PASSWORD_FILE")"
fi
"$COMPANION_ROOT/android/gradlew" -p "$COMPANION_ROOT/android" --no-daemon assembleRelease lintRelease
COMPANION_OUTPUT="$COMPANION_ROOT/../galaxy/bin/starpilot-companion.apk"
cp "$COMPANION_ROOT/android/app/build/outputs/apk/release/app-release.apk" "$COMPANION_OUTPUT"
python3 - "$COMPANION_ROOT/android/app/build/outputs/apk/release/output-metadata.json" "$COMPANION_OUTPUT.version" <<'PY'
import json
import pathlib
import sys
metadata = json.loads(pathlib.Path(sys.argv[1]).read_text())
pathlib.Path(sys.argv[2]).write_text(metadata['elements'][0]['versionName'] + '\n')
PY
printf 'Release APK: %s\n' "$COMPANION_OUTPUT"
