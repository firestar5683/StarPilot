# Screen brightness and Standby

Screen Management provides independent driving and parked brightness preferences in New Galaxy and the native comma 3/3X and comma 4 interfaces.

## Brightness

Auto remains the default. It uses the existing automatic brightness calculation and applies an offset from -30% to +30% of that result. For example, a normal automatic value of 40% with a -30% offset produces 28%, not 10%. The final automatic value is clamped to 5–100% while awake. Standby and normal parked sleep can still deliberately blank the screen.

The existing onroad calculation follows camera exposure and filters changes. Parked Auto retains the existing base level: 50% on comma 3/3X and 65% on comma 4, with existing screen overrides still applied. This feature does not add an offroad ambient-light sensor.

Manual allows 0–100% and starts at 100% when there is no previous manual choice. Each context remembers its own manual value when switched to Auto. Existing manual selections remain selected. Touch and ignition changes temporarily make manual 0% visible at 5%; recognised button presses do so when their wake toggle is enabled. As in Dom, manual onroad 0% suppresses automatic engagement and alert wakes; the same rule applies to the optional turn-signal wake.

New Galaxy shows a mode selector and the slider for that mode. Standby uses the normal Galaxy toggle styling and an enabled-only Manage/Close submenu containing the onroad timeout and wake choices. Native settings provide the same preferences using their existing screen sizes and navigation patterns.

## Timeouts and wake choices

Both timeout readouts use seconds, with a 5–60 second range and 5 second steps. The parked timeout controls normal offroad sleep. The onroad timeout and wake choices are visible when Standby is enabled; the onroad timeout also remains the internal temporary-visibility duration for manual 0%.

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

Engagement and alert detection use Dom's existing status and alert predicates. Entering override alone does not wake. A selected alert keeps resetting the timer while it remains reported. Primary alerts take precedence over the secondary StarPilot alert state, as in Dom; this code does not duplicate renderer-generated alerts or add a separate freshness policy. Wake preferences only affect the display, not the alert or its sound.

Dom's ignition transitions, screen-setting changes and page timeout handling are retained. There are no gear, brake-pedal or accelerator wake triggers. Standby powers the display down after the timeout using Dom's existing display-power path.

Vehicle buttons use the car interface's existing decoded `carState.buttonEvents`. The existing UI subscriber drains every message so short presses survive between UI refreshes, while UI state and frequency tracking receive only the latest frame. No additional vehicle-message reader is opened. Controller buttons use the existing input-device reader. When button wake is enabled, fresh presses wake once; releases, key repeat and held buttons do not keep extending the timer. Mapped actions retain their separate enable setting and continue to work normally. Button coverage depends on what the existing vehicle interface and supported input devices expose; this PR introduces no manufacturer-specific CAN decoding.

## Persistence and compatibility

The existing brightness keys retain 101 as Auto and 0–100 as Manual. Four additional persistent integers store manual memory and relative offsets. Seven persistent booleans store wake selections. StandbyButtonPressTime carries fresh external-controller button timestamps in RAM, clears on manager start, and is excluded from logging.

Native UI and Galaxy writes use one shared validator and an advisory nonblocking file lock outside the Params key directory. Snapshot, write, readback and rollback run within that transaction; UI caches invalidate inside and after it. A busy or failed save is reported and can be retried. Other direct Params writers must use the shared helper to participate in this transaction contract.

The Params registry source must be included in the normal device build before installation. Source changes alone do not update an existing compiled native registry.

## Focused verification

From a configured Linux checkout with the project Python dependencies:

```sh
PYTHONPATH=. python -m pytest -q -c /dev/null --confcutdir=starpilot/common/tests \
  starpilot/common/tests/test_screen_*.py \
  selfdrive/ui/tests/test_native_screen_controls.py \
  selfdrive/ui/tests/test_native_screen_save_errors.py \
  starpilot/system/wheel_controls/tests

PYTHONPATH=. python -m pytest -q -c /dev/null --confcutdir=starpilot/system/the_galaxy/tests \
  starpilot/system/the_galaxy/tests/test_device_settings_frontend.py \
  starpilot/system/the_galaxy/tests/test_device_settings_layout.py \
  starpilot/system/the_galaxy/tests/test_ui_vue_frontend.py \
  starpilot/system/the_galaxy/tests/test_frontend_module_graph.py

node starpilot/system/the_galaxy/tests/test_screen_settings_dom.cjs
```

The DOM test requires Playwright and Chromium. PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE can point to an existing installation; GALAXY_DOM_SCREENSHOT optionally saves previews. It loads the real Vue components with synthetic API responses and no device writes. The Python commands bypass unrelated manager-wide fixtures and explicitly include starpilot tests, which are outside the repository's default testpaths. A fully built environment can additionally run selfdrive/ui/tests/test_device_screen_settings.py through the normal pytest configuration.

Automated tests cover every wake choice enabled and disabled, generic-button freshness, held inputs, Dom status and alert behavior, minimum brightness, write failures, cross-process saves, native controls, browser interactions and existing controller actions. Physical screen readability and actual car input coverage still require checks on the relevant hardware.
