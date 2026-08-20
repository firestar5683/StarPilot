#!/usr/bin/env python3
"""
joystick_probe.py — identify a gamepad's axis codes and value ranges so you can
add it to joystick mode.

WHY THIS EXISTS
  Joystick mode (tools/joystick/joystick_control.py) maps a physical controller's
  sticks to steering + gas/brake. Every controller model reports its sticks under
  different evdev axis codes AND different raw value ranges, so joystick_control.py
  keeps a CONTROLLER_PROFILES table. This probe is how you discover the two facts
  you need to add a new row to that table:
    1. which axis CODE the left-stick-horizontal and right-stick-vertical emit
    2. the raw value RANGE those axes span (and whether it is signed or unsigned)

HOW TO RUN (on the comma device, offroad, controller plugged in)
    cd /data/openpilot && python tools/joystick/joystick_probe.py
  (If it says "Permission denied", run it through python as above rather than
  executing the file directly — it just isn't marked executable.)

  Then move ONE stick/axis at a time, fully in both directions, and watch the
  output. Each line shows:  the axis CODE, its current value (state), and the
  min/max range it has spanned so far.

WHAT TO RECORD  (joystick mode uses exactly two axes)
  * STEER  = left stick, horizontal  -> push left and right, note the CODE
             (usually ABS_X) and its range_so_far (e.g. -32768..32767 or 0..255)
  * ACCEL  = right stick, VERTICAL   -> push up and down, note the CODE
             (Xbox: ABS_RY, Stadia: ABS_RZ, DualSense: ABS_RY) and its range
  Also note the controller NAME printed under "Detected gamepads:" — a unique
  substring of it is the table key used to auto-detect this pad.

INTERPRETING THE RANGE
  * If the values swing symmetrically around 0 (e.g. -32768..32767) the pad is
    SIGNED 16-bit, centered at 0.        -> lo=-32768, hi=32767
  * If the values swing around ~128 within 0..255 the pad is UNSIGNED 8-bit,
    centered at 128.                     -> lo=0,       hi=255
  * The rest/center value doesn't matter for the table — only the endpoints do.
    joystick_control.py maps lo -> -1 and hi -> +1 via np.interp, so center lands
    near 0 automatically as long as lo/hi are the true extremes.

ADDING YOUR CONTROLLER  (edit tools/joystick/joystick_control.py)
  Add a row to CONTROLLER_PROFILES keyed on a substring of the controller name:

      'MySubstr': {'name': 'MyPad', 'steer': '<steer code>', 'accel': '<accel code>',
                   'lo': <min>., 'hi': <max>.},

  e.g. for the Xbox One pad ("Microsoft X-Box One pad"):
      'X-Box': {'name': 'Xbox', 'steer': 'ABS_X', 'accel': 'ABS_RY',
                'lo': -32768., 'hi': 32767.},

  Notes:
  * accel is the right stick's VERTICAL axis; up = gas, down = brake. The leading
    minus sign in joystick_control.py's normalization makes "up = positive accel"
    for BOTH signed and unsigned ranges, so you do NOT need a flip/remap.
  * Keys are matched by substring against the reported name, so 'X-Box' matches
    "Microsoft X-Box One pad (Firmware 2015)". Pick a substring unique to your pad.
  * On-device controllers get a 0.10 deadzone (absorbs stick drift). If your pad
    creeps at rest, that's the knob to raise.

VERIFYING  (after editing and restarting the joystick process)
  With joystick mode on, the on-screen Gas/Steer numbers should move. Those come
  from carControl.actuators, not raw axes, so they only move when the engagement
  gate passes (steer needs lateral active/AOL; gas needs full openpilot long).
  To confirm raw input independently, watch the testJoystick message directly.

TROUBLESHOOTING
  * "Detected gamepads: <none>"  -> the `inputs` library can't see the pad. It's a
    driver/enumeration problem, not a mapping one; no table edit will help until
    the pad is detected. Try re-plugging or a different USB port/cable.
  * All values stay at 0 while a stick moves -> the code column will still change;
    if it doesn't, that physical axis isn't emitting events under any code.
"""
import sys

try:
  from inputs import get_gamepad, devices, UnpluggedError
except Exception as e:
  print(f"inputs import failed: {e}")
  sys.exit(1)

print("Detected gamepads:")
if not devices.gamepads:
  print("  <none>  -> 'inputs' does not see your controller (driver/enumeration issue)")
else:
  for g in devices.gamepads:
    print(f"  {g}")

print("\nMove ONE stick at a time, fully both ways. Note the CODE + range for:")
print("  STEER = left stick horizontal   |   ACCEL = right stick vertical")
print("Ctrl-C to stop.\n")
seen = {}
while True:
  try:
    for ev in get_gamepad():
      if ev.ev_type in ("Absolute", "Key"):
        lo, hi = seen.get(ev.code, (ev.state, ev.state))
        seen[ev.code] = (min(lo, ev.state), max(hi, ev.state))
        rng = seen[ev.code]
        print(f"type={ev.ev_type:9s} code={ev.code:12s} state={ev.state:<8} range_so_far={rng}")
  except (OSError, UnpluggedError):
    print("get_gamepad() raised UnpluggedError -> controller not readable")
    break
  except KeyboardInterrupt:
    break
