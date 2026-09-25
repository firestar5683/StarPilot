# Runtime performance captures

`performance.py` reads existing local messages and Linux process statistics for a fixed duration, then writes one JSON report. It does not start publishers, change settings, restart processes, select models, or connect to another machine. The comparison command reads two saved files only.

From the source checkout, using the configured host runtime:

```sh
./dev python -m tools.diagnostics.performance capture --duration 30 --rate 20 --output /tmp/performance-before.json
./dev python -m tools.diagnostics.performance compare /tmp/performance-before.json /tmp/performance-after.json --output /tmp/performance-comparison.json
```

On a Linux runtime, use its existing Python environment. A privately staged standalone copy can identify the checkout explicitly:

```sh
python /path/to/performance.py capture --source-root /path/to/checkout --duration 5 --output /tmp/performance.json
```

No deployment or device connection is performed by these commands. Run from the runtime environment whose local messages you intend to observe. `--source-root` identifies source metadata; it does not change imports or select a running checkout. The report records the declared source root, imported `openpilot` root, whether they match, loaded messaging module path, checkout HEAD/dirty state, relevant source hashes, and a separate hash of the collector itself. These identify inspected source, not proof that existing processes were built from that HEAD.

`--pid 1234` adds a local process to the manager-reported running PIDs and may be repeated. When no manager message is available, only explicit PIDs are sampled. No process is launched or scanned by name. Process names from manager are recorded as `requestedName`, alongside the kernel's `comm`, PID, and start ticks.

## Limits and output

Defaults are 30 seconds at 20 polls per second. Duration is limited to 0.1–120 seconds, rate to 1–50 Hz, processes to 64 per poll, and retained process instances to 256. Samples stay in memory until one final report is written; there are no per-frame file writes. Slow polls skip schedule slots instead of creating catch-up bursts. The report includes actual duration, poll intervals, missed scheduled polls, and truncation counters. Existing output files are refused.

Each distribution contains sample count, missing counts by reason, min/mean/p50/p90/p95/p99/max. Percentiles use linear interpolation over the retained values. No samples produce `null` statistics, never invented zero values. Real zero measurements remain zero.

Message availability distinguishes an unavailable backend, a backend error, and a working subscription with no observed messages. Linux process availability separately distinguishes absent `/proc`, no process targets, unreadable processes, permission errors, and disappearing processes. A macOS capture can still collect messages; `/proc` CPU and RSS remain unavailable.

## What the measurements mean

| Measurement | Meaning and limit |
|---|---|
| `observedReceiveRateHz` | Fresh messages actually received divided by capture duration. Subscriptions conflate; the collector can miss intermediate messages. This is **not** publisher frequency, UI FPS, execution rate, or a dropped-frame count. |
| `receiveAgeMs` | Time since this collector last received a message, sampled every poll after first receipt. Includes periods without updates. |
| `publicationAgeAtReceiveMs` | Collector monotonic time minus `Event.logMonoTime` at receipt. Includes scheduling and transport delay. Assumes the local publisher uses the same monotonic clock; replay or other clock domains may violate that assumption. Zero and future timestamps are reported missing, with a reason. |
| `reportedFrameIntervalMs` | `uiDebug.frameTimeMillis`, the existing Raylib frame interval. |
| `reportedPrePresentWallMs` | `uiDebug.cpuTimeMillis`. Despite its schema name, the current publisher measures monotonic **wall time** for drawing/update before presentation. It is not thread CPU or presentation duration. |
| `reportedModelExecutionMs` | `modelV2.modelExecutionTime` converted from seconds to milliseconds. The publisher measures its `model.run` interval. This is not sensor-to-actuator latency. |
| `reportedFrameDropPercent` | The existing model publisher's `frameDropPerc`, not a drop rate inferred from collector message counts. |
| Device metrics | Reported utilization, maximum temperature, power, CPU-core mean/max; negative numeric values and missing fields have explicit missing counts. A schema's default zero cannot prove that a hardware sensor is implemented. |
| `cpuPercentOneCore` | Delta process user+system ticks divided by elapsed time and clock frequency. 100% means one logical CPU; a multithreaded process may exceed 100%. Includes no child-process CPU. |
| `rssMiB` | Resident pages from `/proc/PID/stat`, converted using the system page size. Not total allocation, GPU memory, or swapped memory. |

Raw message validity counts are retained; reported metrics are not silently discarded when `valid` is false. In particular, the current `uiDebug` publisher does not set the envelope's default false validity flag. Distributions count fresh received values only, not repeated samples of a stale payload. Reported onroad, engagement, thermal, device and big-model states provide comparison context.

Processes are separated by `(PID, start ticks)`. CPU requires a prior observation of that exact instance. Disappearance, counter regression, or PID reuse resets the baseline. `observedInstanceCountsByName` can reveal multiple observed instances across changed PIDs; `pidReuseOrRestartEvents` counts only identity changes directly observed at a reused PID. Neither is a complete system restart log. Retained names are manager labels, not proof a stale manager PID still belongs to that service.

Existing `UI_FRAME_TIMING=1` instrumentation separately measures drawing, update, and presentation wall/thread CPU time. This tool does not enable it or parse its logs. `collectorEnvironment.UI_FRAME_TIMING` describes the collector's environment, not the settings of an already-running UI.

## Compare captures

The comparison provides key UI/model/device measurements, per-process peak CPU/RSS, full scalar deltas, sample counts, source context, and environment/sampling differences. Missing values remain `missing_data`. Percentage change from a zero baseline is `null`. Process peaks group observed instances by requested name; per-instance percentiles are never averaged into a misleading pooled percentile.

Use the same duration, poll rate, workload, display state, model, and hardware when interpreting differences. Screen-off/offroad captures may legitimately lack UI or model messages. A lower observed message rate is not automatically slower execution. The report makes descriptive comparisons; it does not label a change as a performance regression or certify onroad reliability.

Focused tests (standard library compatible):

```sh
python -m unittest tools.diagnostics.tests.test_performance
```

## Offline longitudinal trace

`longitudinal.py` reads one existing local rlog or qlog segment and prints one JSON object. It never opens a device, starts a publisher, or writes a log. Example: `./dev python -m tools.diagnostics.longitudinal /absolute/path/2-rlog.zst` (the `./dev` wrapper prints its own build progress before the tool's JSON). The report records input and source hashes, limits, message counts, mode transitions, rejected pairs and distributions.

`longitudinalPlan.aTarget` is the planner's acceleration target; `carControl.actuators.accel` is the actuator command; `carState.aEgo` is the vehicle's speed-derived acceleration estimate, not an IMU measurement. The reported delta rates are sample-to-sample derivatives within continuous, same-source/experimental/long-active/pedal stretches. They are not physical jerk, publisher rates, proven road jitter, or evidence that a particular control tune is safe. qlog sampling is decimated. See `python -m unittest tools.diagnostics.tests.test_longitudinal` for synthetic gap/mode/invalid-message coverage.
