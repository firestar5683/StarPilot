# Usage statistics

The optional manager worker reports to `stats.firestar.link` after a drive and
once after startup with a valid clock. It starts requests only while offroad.
Reporting failures do not affect manager process health or engagement.

Galaxy's **Device & Data → Share Usage Statistics** controls reporting. It
defaults on, preserves an explicit opt-out, and is independent of metered log
uploads. Reports contain the branch and commit, device type, vehicle fingerprint,
last verified running model, cumulative usage, regional location, and settings.
They exclude VIN, recordings, passwords, pairing credentials, and exact GPS.
Location lookup receives whole-degree coordinates and reports a nearby city
center when available, otherwise the coarse coordinates.

Settings come from the existing typed UI owners. Ordinary Boolean, bounded
numeric, and fixed-choice rows are collected automatically. Raw Params dumps,
source documents, actions, free text, and user-defined sound-pack names are
excluded. Each field records the saved value and its owner-defined default where
available; it does not imply that the feature was actively controlling the car.

The existing Influx write API uses organization and bucket `StarPilot`. Provision
a write-only credential through `STARPILOT_STATS_TOKEN`, or a regular private
file at `/data/starpilot/analytics/token` (mode `0600`, owned by root or the
manager user). `STARPILOT_STATS_TOKEN_FILE` can select another file. Credentials
must not be committed to source. Missing credentials leave reporting inactive.
`UsageStatsStatus` records the local reporting state without secrets or response
bodies. `UsageStatsState` retains counters and sanitized last-drive context.

Run the mocked network, privacy, owner, and lifecycle checks with:

```sh
./dev python -m pytest -q openpilot/starpilot/analytics/tests
```

These checks also run in `./test`. No test sends statistics to production.
