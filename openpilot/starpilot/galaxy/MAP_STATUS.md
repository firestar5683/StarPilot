# Local map observation

The authenticated loopback-only `/api/maps/status` endpoint lazily subscribes
to MapdOut. It decodes bounded packets with the existing source-aware map
tracker and returns only an unqualified state and optional candidate speed,
with accepted road status, GPS source/age, tile state, and restart/switch counts.
It does not return coordinates, road names, way IDs, raw packets, or a control
decision. It reads no map files or persistent settings. The browser displays
this on Navigation & Maps only in local mode; the static preview remains an
unavailable illustration.

Authentication is checked before sampling and again before sending a result.
The subscriber uses the host boot-time clock and a bounded nonblocking drain;
session loss, malformed packets, source loss, age expiry, and busy/unavailable
transport cannot turn an old candidate into a current one. The browser polls
every 125 ms while mounted without hiding a still-fresh card, expires it at
the remaining event/computation/GPS deadline, rejects delayed responses, and
stops while the tab is hidden before refreshing on return. Server close
releases the observation source. The endpoint does not start Mapd.
