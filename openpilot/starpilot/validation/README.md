# Control-mode evidence contract

This module validates recorded evidence. It does not select a driving mode, drive
actuators, change a safety hook, activate a vehicle policy, or qualify a release.
The initial tests contain synthetic validator fixtures only.

`control-trace.schema.json` describes the JSON format. Run one trace with:

```sh
python -m openpilot.starpilot.validation.control_modes trace.json --output report.json
```

`validate_trace(document)` checks one declared scenario.
`validate_matrix(documents, configurations)` requires every named scenario for
each exact configuration. Its configuration identity includes source, schema,
CarParams, settings, firmware, safety binary, policy, adapter, device and harness.
The caller must enumerate actual configurations; a platform name alone is not a
configuration inventory. Extra metadata is retained in the configuration identity.

| Selected mode | Host lateral may be active | Host longitudinal may be active |
|---|---|---|
| off | no | no |
| lateral_only | yes | no |
| longitudinal_only | no | yes, only with system ownership |
| combined | yes | yes, only with system ownership |

Selection is distinct from instantaneous request, safety permission, effective
host state, decoded active control commands and displayed state. Permission does
not by itself mean an axis is active. Command activity means an active actuator
request decoded using the identified vehicle adapter; receipt of a neutral CAN
packet or a safety allowlist decision alone does not establish it. Missing control
CAN must be recorded as unknown, not inactive. Stock ACC activity is a separate
observation and cannot be substituted for host longitudinal commands.

Each axis records a policy-interpreted blocking fault and input freshness. The
validator does not infer fault scope from alert text, decide which pedal cancels
which axis, or invent a common recovery rule. Each frame supplies explicit expected
effective, command and displayed states from the named vehicle policy. A selected
indicator may intentionally remain visible while authorization is suppressed.
Vehicle policies must preserve deliberate activation-button mappings, pedal and
standstill behavior, steering overrides, cancellation and recovery semantics.

The matrix requires all four steady modes plus brake, gas, standstill, gear change,
steering override, each axis fault, stale input, permission revocation, cancel,
policy recovery, restart and stock ACC handoff cases. Unsupported requested modes
must demonstrate denial. Steady supported modes require observed active samples;
an all-inactive trace cannot qualify an active mode. Event cases require their
named event and explicit expected states. Event annotations and hashes are supplied
by the adapter; this module does not independently authenticate a recording or
prove that an annotated physical transition occurred. The adapter, policy and
event extraction therefore require separate review and replay tests. An inapplicable
scenario needs an explicit vehicle-policy denial case; it is not silently skipped.

Results preserve `errors`, `failures` and `uncovered` findings together:

- `error`: malformed input prevents reliable evaluation.
- `failed`: an observed invariant or explicit policy expectation is violated.
- `uncovered`: observations, provenance, intervals, events or active samples are missing.
- `pass`: this declared trace contract is satisfied within its reported scope.

Missing axes, unknown booleans, stale feedback and absent CAN never become zeroes.
A synthetic trace can pass its unit contract but cannot satisfy the recorded matrix
gate. A failure is retained even when another run of the same case passes. Every
report states `vehicle_qualification: not_established`; a passing matrix is only
coverage of the supplied configurations and scenarios, not a fleet safety claim.

No production trace adapter or reviewed vehicle policies are installed yet. No
vehicle matrix is currently qualified by these fixtures. Fresh-install AOL defaults
and preservation of existing saved preferences belong to the separate state
migration contract, not to this observation validator.
