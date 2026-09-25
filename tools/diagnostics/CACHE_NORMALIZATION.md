# Normalize current Event caches before changing source

`normalize_event_caches.py` explicitly rewrites valid current-schema v1 Event cache envelopes as service-specific v2 envelopes. It does not reset calibration or learned values, change CarParams caches, enable any control feature, or upgrade caches while reading them.

Run only after stopping every cache producer and **before replacing the source or compiled schemas**. The Python environment must load the exact schema that wrote the v1 cache, with the reviewed v2 cache writer available. The normalizer first validates every present eligible cache using the existing exact current-schema metadata/digest contract and fully decodes it. Incompatible metadata, malformed payloads or unreadable values reject the entire batch before any cache is changed.

```sh
python -m tools.diagnostics.normalize_event_caches \
  --params-path /existing/params-root \
  --backup-dir /private/cache-backups \
  --producers-stopped
```

The explicit Params root and its active `OPENPILOT_PREFIX` namespace (default `d`) must already exist. The flag records the caller's assertion; the tool does not stop processes or prove they are stopped. The backup directory must be private and outside Params.

Eligible keys are `CalibrationParams`, `LiveParametersV2`, `LiveTorqueParameters`, and `LiveDelay`. Missing keys remain missing. Valid v2 envelopes remain byte-for-byte unchanged. All CarParams keys remain untouched.

For each v1 cache the existing `put_cache` writer serializes a fully decoded current typed message into a prepared v2 envelope; decoded values are compared before writing. All eligible originals are backed up and read back before replacements. The normalizer holds the native Params lock, compares all originals again, atomically replaces each changed cache, and checks exact readback. Its JSON receipt records the loaded codec/tool paths and hashes, before/after envelope identities, backup location and attempted/completed writes. An I/O failure stops the batch and retains the originals; replacement across multiple keys is not one atomic transaction. Do not automatically restore over a newer source value.

A separately staged copy of `openpilot/starpilot/schema_cache_normalize.py` can be loaded with `runpy.run_path` while imports still point to the verified old checkout. Its API is `normalize_current_event_caches(params, backup_dir, producers_stopped=True)`. This is useful for a future offline updater: normalize and verify under the old runtime, then switch source and run the candidate's read-only startup preflight before starting producers.

A v1 cache that was not normalized before an incompatible schema change still requires a reviewed source-aware migration. This command cannot normalize that cache by merely changing its fingerprint. A runtime whose writer still only emits v1 also cannot perform this operation without a separately reviewed, pinned v2 writer compatible with its old compiled schemas.
