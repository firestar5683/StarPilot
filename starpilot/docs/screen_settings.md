# Screen brightness and Standby

Screen Management provides independent driving and parked brightness preferences in Galaxy.

## Brightness

Auto remains the default. It uses the existing automatic brightness calculation and applies an offset from -30% to +30% of that result. For example, a normal automatic value of 40% with a -30% offset produces 28%, not 10%. The final automatic value is clamped to 5–100% while awake. Standby and normal parked sleep can still deliberately blank the screen.

The existing onroad calculation follows camera exposure and filters changes. Parked Auto retains the existing base level: 50% on comma 3/3X and 65% on comma 4, with existing screen overrides still applied. This feature does not add an offroad ambient-light sensor.

Galaxy shows a mode selector and the slider for that mode. Standby uses the normal Galaxy toggle styling and an enabled-only Manage/Close submenu containing the onroad timeout and wake choices.

## Timeouts and wake choices

Both timeout readouts use seconds, with a 5–60 second range and 5 second steps. The parked timeout controls normal offroad sleep. The onroad timeout and wake choices are visible when Standby is enabled; the onroad timeout also remains the internal temporary-visibility duration for manual 0%.

**Keep Screen On While eGPU Loads** is an optional setting under Screen Settings, off by default. On comma 3/3X and comma 4 it keeps the driving screen visible while the eGPU model is loading, including when Standby or manual 0% brightness would otherwise blank it. After loading finishes, the normal inactivity timeout resumes. Explicit Screen Off actions still take precedence; parked screen sleep is unchanged.

Touch and ignition changes always wake Standby, as in Dom. The **Bluetooth or steering wheel button** toggle enables waking from recognised Bluetooth/USB/controller and steering-wheel button presses, including buttons without an assigned action. This toggle defaults to off. There are no touch or ignition wake toggles and no additional controller actions to configure.

| Wake choice | Default | Trigger |
| --- | --- | --- |
| Engagement | On | UI status changes to engaged, including returning from override |
| Disengagement | On | UI status changes to disengaged, including returning from override |
| Informational alerts | On | Dom reports an informational onroad alert |
| Warning alerts | On | Dom reports a warning onroad alert |
| Critical / takeover alerts | On | Dom reports a critical or takeover onroad alert |
| Turn signals | Off | Signal activation or direction change |
| Bluetooth or steering wheel button | Off | Recognised button press, including unassigned buttons |

Engagement and alert detection use Dom's existing status and alert predicates. Entering override alone does not wake. A selected alert keeps resetting the timer while it remains reported; wake preferences only affect the display, not the alert or its sound.

Vehicle buttons use the car interface's existing decoded `carState.buttonEvents`. The existing UI subscriber drains every message so short presses survive between UI refreshes, while UI state and frequency tracking receive only the latest frame. Controller buttons use the existing input-device reader. When button wake is enabled, fresh presses wake once; releases, key repeat and held buttons do not keep extending the timer. Mapped actions retain their separate enable setting and continue to work normally. This feature introduces no manufacturer-specific CAN decoding.

## Persistence and compatibility

The existing brightness keys retain 101 as Auto and 0–100 as Manual. Four additional persistent integers store manual memory and relative offsets. Seven persistent booleans store wake selections. StandbyButtonPressTime carries fresh external-controller button timestamps in RAM, clears on manager start, and is excluded from logging.

Galaxy and UI-state writes use one shared validator and an advisory nonblocking file lock outside the Params key directory. Snapshot, write, readback and rollback run within that transaction; caches invalidate inside and after it. A busy or failed save is reported and can be retried. Other direct Params writers should use the shared helper to participate in this transaction contract.

## Focused verification

From a configured Linux checkout with the project Python dependencies:

```sh
PYTHONPATH=. python -m pytest -q -c /dev/null --confcutdir=starpilot/common/tests \
  starpilot/common/tests/test_screen_*.py \
  selfdrive/ui/tests/test_device_screen_settings.py \
  starpilot/system/wheel_controls/tests

PYTHONPATH=. python -m pytest -q -c /dev/null --confcutdir=starpilot/system/the_galaxy/tests \
  starpilot/system/the_galaxy/tests/test_device_settings_frontend.py \
  starpilot/system/the_galaxy/tests/test_device_settings_layout.py \
  starpilot/system/the_galaxy/tests/test_ui_vue_frontend.py \
  starpilot/system/the_galaxy/tests/test_frontend_module_graph.py

node starpilot/system/the_galaxy/tests/test_screen_settings_dom.cjs
```

The DOM test requires Playwright and Chromium. `PLAYWRIGHT_MODULE` and `CHROMIUM_EXECUTABLE` can point at an existing installation; `GALAXY_DOM_SCREENSHOT` optionally saves previews. It loads the real Vue components with synthetic API responses and no device writes. The Python commands bypass unrelated manager-wide fixtures and explicitly include StarPilot tests, which are outside the repository's default testpaths.

Automated tests cover wake choices, generic-button freshness, held inputs, Dom status and alert behavior, minimum brightness, write failures, cross-process saves, browser interactions and existing controller actions. Physical screen readability and actual car input coverage still require checks on relevant hardware.
