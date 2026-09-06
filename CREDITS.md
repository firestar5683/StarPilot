# Credits and Code Provenance

StarPilot stands on work by comma.ai, FrogPilot, and many other open-source contributors. This
document records provenance that is not adequately represented by StarPilot's historical commit
authorship. It is not an assertion that an upstream contributor endorses, maintains, or is
responsible for StarPilot's adaptation.

## Ford support adapted from BluePilot

StarPilot commit [`3f6ccd104e826643887930b41ad3b4086b833d32`](https://github.com/firestar5683/StarPilot/commit/3f6ccd104e826643887930b41ad3b4086b833d32)
introduced a substantial adaptation of Ford work from BluePilot's `bp-7.0` branch. That commit's
message thanked the project, but it did not record a source revision or preserve the upstream
authors in the code. This file corrects that provenance gap without rewriting published history.

The exact checkout used for the original port was not recorded and therefore cannot now be proven.
At the time of the import,
[`3a838bba6d3d280592c2fd0496b3378977ae25f1`](https://github.com/BluePilotDev/bluepilot/commit/3a838bba6d3d280592c2fd0496b3378977ae25f1),
was the tip of the public `bp-7.0` line. Some imported platform lines instead trace to the
contemporaneous development line at
[`59e3f2f16a38ff0c16d173b0ccddded23aaa1cd8`](https://github.com/BluePilotDev/bluepilot/commit/59e3f2f16a38ff0c16d173b0ccddded23aaa1cd8).
Those histories were merged the next day as
[`e1d051d7ba270261b4455068bd68f1a58db15a4a`](https://github.com/BluePilotDev/bluepilot/commit/e1d051d7ba270261b4455068bd68f1a58db15a4a),
which is the complete `bp-7.0` snapshot used for this audit. This reconstruction is deliberately
recorded as a range rather than pretending that the missing original source SHA can be recovered.

### Upstream authors and work

- **Alan Polk (`alan-polk`)** is the principal upstream author of the Ford curvature controller,
  angle-primary controller, manual-turn behavior, controller integration, and related panda safety
  work. Important lineage commits include
  [`db2bdff05`](https://github.com/BluePilotDev/bluepilot/commit/db2bdff05df103d71df62f45c2a3cb5211aba6e6),
  [`d0aac605f`](https://github.com/BluePilotDev/bluepilot/commit/d0aac605f99d37e9da205e419f7989c1e9eaa386),
  [`8f8d6d15f`](https://github.com/BluePilotDev/bluepilot/commit/8f8d6d15f0a590f42b78de964ffb0d0af7f5d63d), and
  [`97867c1eb`](https://github.com/BluePilotDev/bluepilot/commit/97867c1eb57b7472f6fc3de62f0fef576e5a5497).
- **John Christman** contributed `bp-7.0` lateral integration, platform data, and the upstream
  anti-stall work referenced by StarPilot's recovery logic, including
  [`ec0ab181c`](https://github.com/BluePilotDev/bluepilot/commit/ec0ab181c344dccaae053e763bc6ce269551a2d8) and
  [`9012f7666`](https://github.com/BluePilotDev/bluepilot/commit/9012f76666a5c90764fcaec40832b9a607488c27),
  with additional vehicle data in
  [`f0c6bf51f`](https://github.com/BluePilotDev/bluepilot/commit/f0c6bf51f19bb7b74226ead622cabef56e602125).
- **Jacob Neulight** contributed measured shadow-curvature and steering-pinion curvature/safety
  work, including
  [`699c17d9f`](https://github.com/BluePilotDev/bluepilot/commit/699c17d9fde62c690eed9d68eed7d731744d5137) and
  [`26030f3cb`](https://github.com/BluePilotDev/bluepilot/commit/26030f3cb56a169ab0cf2b5a5ad15fa9af391b10).
- **Nathan Ingraham** contributed the separate high-speed damping adjustment in
  [`1db52bc79`](https://github.com/BluePilotDev/bluepilot/commit/1db52bc79e607ddb00214254dd4d732615e27fe4) and
  [`3610e3f18`](https://github.com/BluePilotDev/bluepilot/commit/3610e3f18a0ad37d793d7ada61dbc739ab1077a3).
- **Praeuner** contributed the damping-range update in
  [`b600a8fdb`](https://github.com/BluePilotDev/bluepilot/commit/b600a8fdb985a2219fad4006ce9444b7071b52da).
- **tonesto7** contributed to the Ford integration and CAN-message history represented in the
  imported branch, including
  [`7f9212f7f`](https://github.com/BluePilotDev/bluepilot/commit/7f9212f7f8dc22c4a0a22443158554f4d3652a3c).
- **Haibin Wen and sunnypilot contributors** are named in file-level notices on upstream Ford
  extension files that informed StarPilot's vehicle-state and lateral-limit integration. Their
  published copyright and license notices are retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Dirk Petersen, Alex Troxel, Kacer Aleks, and other BluePilot contributors** supplied Ford
  fingerprints, VIN/platform data, tests, and integration changes that are represented in the
  imported vehicle-support set. Examples include
  [`3706b5645`](https://github.com/BluePilotDev/bluepilot/commit/3706b5645c270ad83cfecc3e92618924f0963166),
  [`694bdbb7a`](https://github.com/BluePilotDev/bluepilot/commit/694bdbb7a9cc70af04d0118e891df96e47ded7c7), and
  [`a02c06ef3`](https://github.com/BluePilotDev/bluepilot/commit/a02c06ef37acff518a511ba0a88a4dc65f506353).

This list identifies contributors whose work was found during the repository and blame audit. The
BluePilot repository and its Git history remain the authoritative record and may identify further
contributors.

### Local-to-upstream map

| StarPilot area | Upstream lineage | What StarPilot changed |
| --- | --- | --- |
| `starpilot/car/ford/lateral.py` | `human_turn.py`, `lateral_curv_ext.py`, `lateral_angle_ext.py`, and `values_ext.py` at the reference snapshot above | Reorganized three extension/mixin implementations into one controller; integrated StarPilot Params; later added live-delay curvature lookahead, active-session driver override, measured-curvature handoff blending, PSCM acknowledgement, and local recovery/tuning behavior. |
| `starpilot/car/ford/fordcan.py` | `fordcan_ext.py` and the angle-mode safety protocol, especially `8f8d6d15f` | Reduced the extension to the Ford lateral CAN constructors used by StarPilot and adapted it to the local controller interface. |
| `opendbc_repo/opendbc/car/ford/` | Ford controller/state/interface/radar/platform changes in the `bp-7.0` snapshot | Integrated the changes directly into StarPilot's opendbc layout instead of retaining sunnypilot mixins; subsequent fixes and behavior differ by file. |
| `opendbc_repo/opendbc/safety/modes/ford.h` and Ford safety tests | BluePilot panda enforcement for four-signal curvature and angle-primary control, especially `8f8d6d15f`, plus shadow-curvature work | Adapted the flags and checks to StarPilot's smaller mode protocol and continued adding local regression coverage. |
| Ford Params and settings surfaces | BluePilot's mode and tuning concepts | Renamed and implemented in StarPilot's native Params/Galaxy architecture; no BluePilot or sunnypilot UI classes were retained. |

The local code has materially diverged, but the first four rows remain derivative in design and in
parts of their implementation. Future ports should cite the exact upstream commit in the importing
commit and at the relevant source boundary; when history can be retained cleanly, use a merge,
subtree, or cherry-pick with origin metadata rather than a single squashed attribution.

## Policy for future third-party ports

Before publishing a third-party port:

1. Read every repository-level and file-level license that may cover the source. Stop and ask the
   rightsholder when the terms or their scope conflict.
2. Record the repository URL, exact commit SHA, source paths/symbols, authors found in the relevant
   history, and the local destination in the importing commit and this file.
3. Preserve required copyright and license notices verbatim. Reorganization, translation, and
   AI-assisted rewriting do not remove source provenance.
4. Retain authorship/history with a merge, subtree, or `cherry-pick -x` when practical. For a true
   adaptation, keep the local adapter as commit author and use an `Adapted-from:` trailer and source
   comments; do not add `Co-authored-by:` for a person without their agreement.
5. Describe material local deviations and make clear that upstream contributors do not support or
   endorse the downstream version.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for licensing notices.
