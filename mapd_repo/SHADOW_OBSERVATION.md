# Development map observation

`mapd --shadow --offline-root /absolute/path/to/offline` is a separate,
explicit diagnostic path. It requires an existing tile root and does not load
saved Mapd settings or device overrides, start downloads, read MapdIn or CLI commands, or subscribe
to car, model, or selfdrive state. It reads GPS and validated tiles through the
ordinary source selector, loader, matcher, and MapdOut serializer, then publishes
MapdOut only. The matcher uses pure embedded lane/conditional defaults; it does
not open `/data/openpilot/mapd_defaults.json`. Car, model, selfdrive and MapdIn
messages are ignored, and curve/upcoming control calculations are skipped. The
normal provider path is unchanged. SIGINT/SIGTERM stop the diagnostic pump and
close its IPC endpoints.

The shadow initializer explicitly selects the host `msgq_` path and the host
registry's 250 KiB MapdOut queue size. It does not rely on gomsgq's legacy
marker-file fallback or an inherited `USE_MSGQ_PREFIX` value. The still
inactive full-provider path retains its older 2 MiB MapdOut queue table; that
mismatch must be resolved and tested before any full-provider runtime
activation.

The shadow packet retains the road candidate, original GPS time, compute time,
source generation, session, and status. All suggested, accepted, upcoming, and
curve control fields remain neutral. A fresh match is **not** proof of the
correct road. The current matcher may lose availability at adjoining ways or
still select a wrong unique way. No map value from this mode has SLC authority.

This mode is not configured by manager and is not started by default. Tests use
synthetic packed tiles and an explicit temporary root; they do not fetch maps
or start the executable. A required cross-language test uses the real Go pump
and publisher over an isolated IPC namespace into the Python Galaxy reader;
it needs `STARPILOT_SHADOW_IPC_REQUIRED=1` and an absolute `STARPILOT_PYTHON`
with host Capnp/msgq. A later activation review must establish tile
provenance, wrong-road behavior, lifecycle, and consumer qualification before
any map-derived control value is considered.
