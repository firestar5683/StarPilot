# Galaxy local Wi-Fi hotspot

Galaxy's opt-in hotspot gives a phone local browser access while the comma's
primary Wi-Fi interface remains connected to Android Auto (or another Wi-Fi
network). It replaces the retired Galaxy browser Bluetooth companion and PAN
experiment. Uniden, Android Auto Bluetooth discovery, and normal Bluetooth
settings remain supported. No kernel flash or native phone app is required.

## Setup

While parked, open Galaxy through your existing local address or remote tunnel,
sign in, and open **Install Galaxy / Tunnel → Galaxy Wi-Fi Hotspot**. Turn on
**Broadcast hotspot automatically**, set your password, and save. The network
name is fixed to `TheGalaxy-` plus the last four characters of the physical
comma dongle ID (for example, `TheGalaxy-6b86`). A missing/unregistered identity
prevents startup rather than inventing a shared fallback name. The saved switch
and password survive restarts; no browser needs to stay open.
A blank initial password generates a random
24-character password; subsequent blank passwords retain the existing password.
Use **Show password** to view it. Passwords must be 12–63 printable ASCII
characters without spaces. Settings changes require an authenticated, parked
session and reject stale revisions.

Once status is **active**, join that network on the phone, remain connected if
it warns of no Internet, and open **http://172.31.254.1:8082/**. Bookmark the full
address. This is ordinary HTTP over WPA2-protected local Wi-Fi and requires no
Web Bluetooth permissions in Chrome, Firefox, or Safari. Galaxy authentication
still applies. Only share the Wi-Fi password with trusted people: local services
on the comma may also be reachable. Do not enter a reused Wi-Fi password.

The public `galaxy.firestar.link` link remains a separate Internet tunnel; it
does not magically resolve to this hotspot. Internet-dependent Galaxy features
still require Internet. The hotspot supplies neither an Internet gateway nor a
DNS server. IPv6 is disabled only on its interface, and forwarding to/from it is
blocked. The phone's handling of simultaneous cellular Internet varies; Galaxy
local access itself does not need cellular service.

## Lifecycle and limits

- Off by default. Saved settings are private (`hotspot.json`, mode 0600) in the
  Galaxy storage directory. Credentials are never stored in browser storage.
- A dedicated `galaxy0` AP is created on the existing radio. `wlan0` and `p2p0`
  are not reconfigured. Do not enable the system's ordinary tethering toggle:
  its profile takes over `wlan0` and is not this feature.
- With the saved switch enabled, the manager automatically starts the hotspot
  while the comma is running. With no station connection it uses 2.4 GHz channel
  6; with Wi-Fi or Android Auto connected it follows that connection's channel.
  During association/handshake it pauses to give the station priority, and
  recreates the AP after the channel settles. Disconnects return to standalone
  mode. These transitions can disconnect phone clients briefly. A disabled or
  unavailable Wi-Fi radio is not force-enabled. Unsupported/regulatory-restricted channels
  fail closed without changing the station connection or country settings.
- A conflicting route for `172.31.254.0/24` prevents startup. AP readiness is
  checked through hostapd, not inferred merely from a running process.
- The privileged worker receives a pipe heartbeat. EOF, lease expiry, or normal
  shutdown removes its own AP and forwarding rules. A transient systemd service
  owns its child processes so a worker crash cannot leave orphan DHCP/AP
  processes. A uniquely marked stale AP is removed on the next worker start.
  No unrelated interfaces, routes, profiles, or firewall rules are flushed.
- Disable it while parked to stop the AP. Changing credentials disconnects
  clients; reconnect using the new settings. If a save response is lost during
  reconnection, reload to check the saved configuration before retrying.
- This feature runs only on the primary device instance, not desktop previews
  or named `OPENPILOT_PREFIX` test instances.

## Validation status

A temporary concurrent AP on the test comma (AGNOS 19.8.1, kernel 4.9.103,
channel 149) was successfully opened from an iPhone while Android Auto remained
projecting in the same session. That establishes feasibility for that hardware;
it does not establish all-channel or long-drive reliability. The production
lifecycle and browser controls have separate automated tests. The production
worker also passed a bounded offroad test on channel 36: AP readiness, Galaxy
HTTP 200, unchanged station connection, and AP/firewall cleanup on control-pipe
closure and heartbeat expiry. Retest sustained
projection, reconnects, parked configuration, and reboot behavior on the target
before relying on it routinely. Standalone startup and transitions are covered
by unit tests but still need a physical disconnected-radio/reconnect test.
The hotspot is experimental and opt-in.

## Keeping the public hostname offline (not implemented)

The existing remote URL is `https://galaxy.firestar.link/<device-slug>`. DNS
only selects an IP for the hostname, not that path or the local port 8082.
Public dynamic DNS pointing this shared hostname to a private address would
break remote access for other users and would not provide trusted HTTPS.

A local equivalent would require hotspot DNS (split DNS), a local HTTPS
listener on 443, trusted certificate provisioning/renewal controlled by the
domain owner, and explicit path/Host/Origin/authentication handling. The current
local API intentionally rejects a public hostname on the raw HTTP listener.
Do not disable those checks or ship the public site's TLS private key to devices.

Prefer a per-device hostname such as `<device>.galaxy.firestar.link`, with its
own certificate and private key: local DNS can send that device's hostname to
the hotspot while public DNS sends it to the remote service. Giving each comma
a certificate for the same shared hostname would allow a compromised device's
key to impersonate that hostname for other users, even if every key were unique.
This design requires coordination with the Galaxy domain/tunnel operator and
tests for certificate renewal, phone/browser DNS behavior, and session isolation.
