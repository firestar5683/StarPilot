# Exact platform coverage gate

`openpilot/starpilot/validation/required-platforms.json` freezes 345 exact source
platform IDs and seven distinct upstream additions. The source-inventory hash and
revisions make the obligation set reviewable. A shared name or declaration does not
mean that controller, firmware, settings, safety, or physical behavior is equivalent.

Run the reporter with an interface suite's two companion files:

```sh
python tools/ci/fleet_coverage.py \
  --interface-coverage ci-results/interfaces/coverage.json \
  --interface-results ci-results/interfaces/results.json \
  --output ci-results/fleet-coverage.json
```

The default `--require complete` exits zero only when both interface and independent
mode coverage pass. CI and predeploy use `--require interfaces` to require every
exact interface obligation and stable current execution provenance. That choice
does not clear mode gaps: the full report remains `uncovered` when mode evidence
is absent, and `vehicle_qualification` remains `not_established`. The separate
`interface_gate` records only interface errors, failures and gaps. It compares the
exact registry IDs and one concrete interface test per ID, checks every execution
record, verifies the companion results hash, and compares the reported checkout,
suite runner, test runner, dependency manifest, pinned opendbc commit, CAN sources,
and native parser binary with the current checkout. An older report remains visible
under `reported_interface_counts`, while `current_interface_counts` marks its
passing tests as `historical_pass_only`. A missing port or upstream addition remains
uncovered. A skip, missing test, failed test, duplicate, or malformed report never
becomes a current pass. Upstream additions remain independent obligations even if
they disappear from a later registry.
The command refuses to overwrite an existing output file, including a failed or
uncovered report. Use a fresh path for each run. A matching HEAD alone is not
enough for current execution: the recorded before/after source snapshots must
match the current snapshot, including relevant dirty source and native bytes.
Unrelated UI source changes do not invalidate vehicle execution.

Recorded control evidence may be supplied through `--mode-evidence path.json`:

```json
{
  "schema_version": 1,
  "enumeration_complete": true,
  "provenance": {
    "configuration_inventory_sha256": "<64 lowercase hex characters>",
    "trace_catalog_sha256": "<64 lowercase hex characters>"
  },
  "configurations": ["<exact configuration objects>"],
  "traces": ["<control-trace.schema.json documents>"]
}
```

The two SHA-256 values must be computed over their respective JSON arrays using
UTF-8, sorted object keys, compact separators `,` and `:`, no ASCII escaping, and
no trailing newline. For Python, this is
`sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))`.
The gate recomputes both digests; a digest-shaped label alone is insufficient.

Each configuration is the exact object accepted by
`openpilot.starpilot.validation.control_modes`: platform, device, harness, policy,
firmware, settings, schema, safety binary and adapter identities belong in it. The
caller must enumerate every relevant configuration, including hardware and firmware
variants. Platform names alone are not a configuration inventory. All 17 named
scenarios must be covered for every configuration. Synthetic traces cannot satisfy
the matrix; earlier failures remain failures when later traces pass. The `off`,
`lateral_only`, `longitudinal_only`, and `combined` modes retain separate host-axis
and stock ACC ownership checks. A missing mode file, provenance, configuration,
recorded scenario or observation is uncovered.

This gate checks declared data and reported provenance; hashes and recording labels
supplied by a caller do not authenticate a trace adapter or physical origin. Every
output says `vehicle_qualification: not_established`, including a passing coverage
contract. Recorded replay, adapter review, hardware, bus, firmware and release
qualification remain separate work.
