# Screen brightness and Standby

Screen Management provides independent driving and parked brightness preferences in New Galaxy and the native comma 3/3X and comma 4 interfaces.

## Brightness

Auto remains the default. It uses the existing automatic brightness calculation and applies an offset from -30% to +30% of that result. For example, a normal automatic value of 40% with a -30% offset produces 28%, not 10%. The final automatic value is clamped to 5–100% while awake. Standby and normal parked sleep can still deliberately blank the screen.

The existing onroad calculation follows camera exposure and filters changes. Parked Auto retains the existing base level: 50% on comma 3/3X and 65% on comma 4, with existing screen overrides still applied. This feature does not add an offroad ambient-light sensor.

Manual allows 0–100% and starts at 100% when there is no previous manual choice. Each context remembers its own manual value when switched to Auto. Existing manual selections remain selected. A selected wake event temporarily makes manual 0% visible at 5%.

New Galaxy shows a mode selector and the slider for that mode. Standby uses the normal Galaxy toggle styling and an enabled-only Manage/Close submenu containing the onroad timeout and wake choices. Native settings provide the same preferences using their existing screen sizes and navigation patterns.

## Timeouts and wake choices

Both timeout readouts use seconds, with a 5–60 second range and 5 second steps. The parked timeout controls normal offroad sleep. The onroad timeout and wake choices are visible when Standby is enabled; the onroad timeout also remains the internal temporary-visibility duration for manual 0%.

During Standby, only selected conditions reset the wake timer. Changing settings, opening a page, or requesting a page-specific timeout does not independently wake it. Once Standby ends, ordinary parked touch and drive-transition behavior applies again.

| Wake choice | Default | Trigger |
| --- | --- | --- |
| Touch screen | On | Screen touch |
| Car drive state changed | On | Gear, ignition or onroad state changes |
| Bluetooth or steering wheel button | Off | Connected Bluetooth/USB controller button or supported vehicle button press |
| Engagement | On | Assistance becomes enabled |
| Disengagement | On | Assistance becomes disabled |
| Informational alerts | On | A displayed informational alert |
| Warning alerts | On | A displayed warning alert |
| Critical / takeover alerts | On | A displayed critical or takeover alert |
| Turn signals | Off | Signal activation or direction change |
| Brake pedal | Off | Brake press |
| Accelerator pedal | Off | Accelerator press |

Selected alerts keep the screen awake while displayed. Category selection follows the comma 3/4 renderers, including generated startup and unresponsive-system alerts and primary-alert precedence. Hidden or stale raw alerts do not bypass selection. Pedals, signals and buttons use transitions, so holding one does not continually refresh the timer. Disabling an alert wake controls the screen only; it does not change the underlying alert or sound.

Vehicle button coverage depends on the car interface. Generic button events are drained through a nonconflating carState subscription because a single-frame event can disappear between UI frames. Tesla Model 3/Y additionally use a passive subscriber to the existing UI_warning/scrollWheelPressed signal. The Tesla signal detects left/right/down presses, not wheel rotation or a second overlapping press while its aggregate pressed bit remains set. Neither observer transmits CAN nor changes driving button events. Controller actions retain their separate enable toggle; an unmapped button can wake the screen without executing an action.

## Persistence and compatibility

The existing brightness keys retain 101 as Auto and 0–100 as Manual. Four additional persistent integers store manual memory and relative offsets. Eleven persistent booleans store wake selections. StandbyButtonPressTime carries fresh button timestamps in RAM, clears on manager start, and is excluded from logging.

Native UI and Galaxy writes use one shared validator and an advisory nonblocking file lock outside the Params key directory. Snapshot, write, readback and rollback run within that transaction; UI caches invalidate inside and after it. A busy or failed save is reported and can be retried. Other direct Params writers must use the shared helper to participate in this transaction contract.

The Params registry source must be included in the normal device build before installation. Source changes alone do not update an existing compiled native registry.

## Focused verification

From a configured Linux checkout with the project Python dependencies, including the compiled opendbc parser/packer:

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
node starpilot/system/the_galaxy/tests/test_tesla_can_wake_frontend.cjs
```

The DOM test requires Playwright and Chromium. PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE can point to an existing installation; GALAXY_DOM_SCREENSHOT optionally saves previews. It loads the real Vue components with synthetic API responses and no device writes. The Python commands bypass unrelated manager-wide fixtures and explicitly include starpilot tests, which are outside the repository's default testpaths. A fully built environment can additionally run selfdrive/ui/tests/test_device_screen_settings.py through the normal pytest configuration.

Automated tests cover every wake choice enabled and disabled, freshness, held inputs, generated-alert parity, minimum brightness, write failures, cross-process saves, native controls, browser interactions and existing controller actions. Physical screen readability and actual car input coverage still require checks on the relevant hardware.
