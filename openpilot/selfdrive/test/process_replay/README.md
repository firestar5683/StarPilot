# Process replay

Process replay is a regression test designed to identify any changes in the output of a process. This test replays available segments through individual processes and compares the output to a known good replay.

All 16 currently selected recording inputs remain required in a full run. Volvo C1/V40 has no available recording. This exact platform is reported as an unrecorded gap in `coverage.json` and the GitHub job summary; it is not a passing replay. The interfaces job requires its existing host tests, and both native safety jobs require its existing C1 safety tests. New unrecorded brands, changed active Volvo platform scope, missing required test suites, and a newly available Volvo recording require coverage review and fail input accounting. Source/native tests and recorded replay outcomes remain separate evidence; neither this inventory nor the missing-input classification qualifies the fleet.

If the test fails, make sure that you didn't unintentionally change anything. If there are intentional changes, the reference logs will be updated.

Use `test_processes.py` to run the test locally.
Log files are cached by default. Use `DISABLE_FILEREADER_CACHE='1' test_processes.py` to disable caching.

Currently the following processes are tested:

* controlsd
* radard
* plannerd
* calibrationd
* dmonitoringd
* locationd
* paramsd
* ubloxd
* torqued

### Usage
```
Usage: test_processes.py [-h] [--whitelist-procs PROCS] [--whitelist-cars CARS] [--blacklist-procs PROCS]
                         [--blacklist-cars CARS] [--ignore-fields FIELDS] [--ignore-msgs MSGS] [--update-refs]
Regression test to identify changes in a process's output
optional arguments:
  -h, --help            show this help message and exit
  --whitelist-procs PROCS               Whitelist given processes from the test (e.g. controlsd)
  --whitelist-cars WHITELIST_CARS       Whitelist given cars from the test (e.g. HONDA)
  --blacklist-procs BLACKLIST_PROCS     Blacklist given processes from the test (e.g. controlsd)
  --blacklist-cars BLACKLIST_CARS       Blacklist given cars from the test (e.g. HONDA)
  --ignore-fields IGNORE_FIELDS         Extra fields or msgs to ignore (e.g. driverMonitoringState.events)
  --ignore-msgs IGNORE_MSGS             Msgs to ignore (e.g. onroadEvents)
  --update-refs                         Updates reference logs using current commit
```

## Forks

openpilot forks can use this test with their own reference logs, by default `test_proccesses.py` saves logs locally.

To generate new logs:

`./test_processes.py`

Then, check in the new logs through the external test-data catalog. Make sure to also update the `ref_commit` file to the current commit.

## API

Process replay test suite exposes programmatic APIs for simultaneously running processes or groups of processes on provided logs.

```py
def replay_process_with_name(name: Union[str, Iterable[str]], lr: LogIterable, *args, **kwargs) -> List[capnp._DynamicStructReader]:

def replay_process(
  cfg: Union[ProcessConfig, Iterable[ProcessConfig]], lr: LogIterable, frs: Optional[Dict[str, Any]] = None,
  fingerprint: Optional[str] = None, return_all_logs: bool = False, custom_params: Optional[Dict[str, Any]] = None, disable_progress: bool = False
) -> List[capnp._DynamicStructReader]:
```

Example usage:
```py
from openpilot.selfdrive.test.process_replay import replay_process_with_name
from openpilot.tools.lib.logreader import LogReader

lr = LogReader(...)

# provide a name of the process to replay
output_logs = replay_process_with_name('locationd', lr)

# or list of names
output_logs = replay_process_with_name(['ubloxd', 'locationd'], lr)
```

Supported processes:
* controlsd
* radard
* plannerd
* calibrationd
* dmonitoringd
* locationd
* paramsd
* ubloxd
* torqued
* modeld
* dmonitoringmodeld

Certain processes require saved initial state in `Params`, such as `CalibrationParams`
or `LiveParametersV2`. Managed schema caches in `custom_params` must contain verified
envelopes created by `openpilot.starpilot.schema_cache.put_cache` from current-schema
messages whose origin is known. Synthetic current-schema fixtures can use this path.

Historical logs require source schema provenance and an explicit schema-specific
conversion before their values can seed these caches. Reading old bytes through the
current schema does not establish compatibility. `get_custom_params_from_lr` now
refuses this operation, and automatic firmware `CarParamsCache` seeding also refuses
unless a verified envelope was supplied. Configuration is checked before Params
writes. An explicit current vehicle fingerprint can avoid firmware-cache seeding,
but does not qualify the remaining logged messages.

The checked-in replay recording catalog supplies a separate, reviewed firmware
cache adapter. It pins each input and its independently published card reference,
decodes the reference with its producing source schemas, checks firmware/VIN
identity against the recording, and converts the reference CarParams into a
verified current envelope. The current vehicle factory still recomputes control
and safety settings. This adapter does not alter expected outputs or authorize
implicit cache conversion for other historical recordings. Input, reference or
schema changes require a new review; do not regenerate expected outputs to hide
differences.

Default `ref_commit` and unlisted expected logs use the immutable official artifact
revision. Fourteen exact segment/process pairs use reviewed StarPilot references in
`refs/starpilot`, preserving intentional controller and capability changes. Their
manifest pins inputs, comparison configurations, producing source snapshots and
both official and reviewed output hashes. Every original comparison remains active;
an arbitrary local output cannot override a default expectation. Deliberate alternate
`ref_commit` and `--update-refs` retain their local reference behavior.

The EV6 and Bolt EUV control references include the default Turn Assist behavior;
explicit `TurnAssist=False` independently restores every prior compared field.
The legacy Corolla recording contains no native axis or safety acknowledgement,
so its control reference requires both axes disabled and zero torque and acceleration
even when stock enable is true. Actual Controls and native Toyota safety regressions
verify fresh grants and missing acknowledgement denial. The four reference updates
record the prior output hash, exact difference fields and counts, regression source
hashes, and committed producing sources in the manifest. These records document the
reviewed changes; they do not exclude any field from replay comparison.

Use `--output DIRECTORY` to place coverage, new logs and both diff reports outside
the source tree. The predeploy runner supplies its results directory automatically.

Replaying processes that use VisionIPC (e.g. modeld, dmonitoringmodeld) require additional `frs` dictionary with camera states as keys and `FrameReader` objects as values.

```py
from openpilot.tools.lib.framereader import FrameReader

frs = {
  'narrowRoadCameraState': FrameReader(...),
  'wideRoadCameraState': FrameReader(...),
  'cabinCameraState': FrameReader(...),
}

output_logs = replay_process_with_name(['modeld', 'dmonitoringmodeld'], lr, frs=frs)
```

To capture stdout/stderr of the replayed process, `captured_output_store` can be provided.

```py
output_store = dict()
# pass dictionary by reference, it will be filled with standard outputs - even if process replay fails
output_logs = replay_process_with_name(['radard', 'plannerd'], lr, captured_output_store=output_store)

# entries with captured output in format { 'out': '...', 'err': '...' } will be added to provided dictionary for each replayed process
print(output_store['radard']['out']) # radard stdout
print(output_store['radard']['err']) # radard stderr
```
