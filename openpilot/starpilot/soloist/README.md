# Spotify and phone audio

Galaxy → Spotify and Phone Audio supports two mutually exclusive music sources:
Spotify Connect (Soloist) and a paired phone's Bluetooth A2DP audio. Both use the
private PulseAudio output, either Android Auto's PCM media channel or an existing
BlueALSA Bluetooth output. Phone mode needs neither Soloist nor a Spotify API key.
The feature's existing enable flag starts `spotifyd` for either source.

## Phone setup

1. While parked, enable Bluetooth and pair the phone from Galaxy's Bluetooth page.
2. Choose **Phone over Bluetooth**, then select the paired phone.
3. Choose **Android Auto** as the output and connect projection to the head unit,
   or choose a different paired Bluetooth speaker/head unit.
4. Turn on **Phone Audio**. Select the comma as the phone's media audio output,
   then play music. Use the phone and car for playback and volume.

Changing the source stops the previous player. Pairing, source/device selection,
and output changes retain Galaxy's existing session and parked/offroad checks.
Phone calls, microphone forwarding, head-unit metadata and steering-wheel track
controls are not implemented. AVRCP pause is attempted when Android Auto loses
media focus permanently; even if the phone cannot be paused, forwarding relinquishes
focus. The comma's warning speaker and global ALSA default are not changed.

## Companion apps

Pairing a phone in the Android or iPhone companion app also sets it up for phone
audio. The app asks the comma to open a short pairing window (Galaxy's **Let a
phone pair** button does the same). Only one phone can claim it, only phones
(Bluetooth device class) are accepted, and a confirmation code must be approved.
Afterward the phone appears as the music source if none was chosen yet. Android
bonds from the app; on iPhone the app asks you to tap the comma in
Settings → Bluetooth. The window refuses to open while Android Auto, another
pairing, or a search holds the adapter, and adapter visibility returns to what it
was before. The companion's own key pairing never creates a Bluetooth bond.

Installing Soloist is only allowed from the local network, the Galaxy hotspot or
the tunnel. Over the companion's Bluetooth link the page says so and sends nothing.
Phone audio itself needs no install and works over Bluetooth. The Android app and
the iPhone app each carry their own copy of the Galaxy pages, so they show this
page only after they are updated.

## Runtime behavior

The cached AGNOS image's BlueALSA service starts `/usr/bin/bluealsa -p a2dp-source`.
`phone_profile.py`, invoked through noninteractive sudo on the device, temporarily
adds `a2dp-sink` using its own drop-in under `/run/systemd/system/bluealsa.service.d`.
Only BlueALSA is restarted, once on entry and once on exit; Bluetooth bonds,
bluetoothd, adapter power/identity and HFP registration are not changed. Unknown
service commands and externally modified drop-ins are rejected. The override is
removed on orderly shutdown/source change, recovered at the next supervisor start
after an abrupt shutdown, and disappears at reboot. If the supervisor is killed
without restarting, the receiving profile can remain advertised until reboot;
its capture worker exits on parent death. Bluetooth music may briefly disconnect
while BlueALSA restarts. Radio-off is respected; this feature never powers it on.

Only the selected paired phone is captured. The existing trusted pairing policy
still determines which phones may establish Bluetooth connections; this feature
does not alter trust or erase bonds. `arecord` opens an ALSA plug PCM for that
phone, converting to signed 16-bit 48 kHz stereo. A separate Python worker writes
to the private server using AGNOS's `libpulse-simple.so.0`, with bounded buffers.
The supervisor retries disconnects without repeatedly restarting Bluetooth.
No extra native binaries are bundled or built for this feature.

## Validation

Automated tests cover source migration/validation, authenticated settings, parked
selection, no-Soloist startup, radio-off, disconnect/retry, temporary-profile
restoration, selected-phone AVRCP targeting, and clearing audio on source changes.
Run the Soloist, Galaxy Spotify setup, and Android Auto media-audio Python tests,
plus `node openpilot/starpilot/galaxy/tests/test_spotify.mjs`.

Device acceptance remains necessary: test Android/iPhone pairing and audio,
44.1/48 kHz tracks, radio focus loss/resume, phone disconnect/reconnect, Bluetooth
off/on, source switching, service restart and reboot. Test wireless Android Auto
and Bluetooth output separately for radio coexistence, latency and dropouts.
