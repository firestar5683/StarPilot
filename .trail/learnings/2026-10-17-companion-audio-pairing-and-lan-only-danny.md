---
title: Companion audio pairing and LAN-only Soloist install
author: Danny
date: 2026-10-17
branch: Stardust-Spotify
cost: { minutes: 29, tokens: 110916 }
touches:
  - openpilot/starpilot/bluetooth/owner.py
  - openpilot/starpilot/galaxy/http_server.py
  - openpilot/starpilot/galaxy/server.py
  - openpilot/starpilot/galaxy/spotify_setup.py
  - openpilot/starpilot/galaxy/tests/test_bluetooth.mjs
  - openpilot/starpilot/galaxy/tests/test_bluetooth_http.py
  - openpilot/starpilot/galaxy/tests/test_spotify.mjs
  - openpilot/starpilot/galaxy/tests/test_spotify_setup.py
  - openpilot/starpilot/galaxy/web/data/catalog.json
  - openpilot/starpilot/galaxy/web/js/bluetooth.js
---

## Decided
- The companion app key pairing never makes a Bluetooth bond, so phone audio needs its own comma pairing window (`BluetoothOwner.accept_pair`). It takes one phone-class device, needs the code approved, journals adapter visibility, and shares the Android Auto admission lock.
- Soloist upload is refused from loopback (the Bluetooth bridge's path) and allowed from LAN, hotspot and the tunnel (`install_origin_allowed`).
- iPhone cannot start a classic bond from an app, so it opens the window and the user taps comma in Settings.
- Work is split: comma side in Stardust-Spotify, bridge and apps in worktree `../openpilot-companion` (companion-secretgood-v2).

## Tried and ruled out
- Testing the tunnel upload path through the test server: remote-transport sessions reject the local cookie, so test the pure policy function instead.
- `journal_path` as a property on the base owner: it clashed with the attribute the Android Auto subclass sets and broke 28 AA tests; it is named `window_journal_path`.

## Watch out
- The phone-class check is untested on a real phone; if a phone reports no class the window ignores it.
- Opening the window restarts the BlueALSA service once, so music can drop briefly.
- The apps ship their own copy of the Galaxy web pages, so the new Bluetooth page needs an app rebuild; the APK needs the user's signing key.
- Mac test runs need an ELF-stub runner plus a Params stub; the 3 `test_owner.py` msgq failures also fail on the original code.
