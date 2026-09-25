# Independent lateral and longitudinal control

AOL connects Card button intent, SelfdriveD axis decisions, Controls output,
driver monitoring and acknowledged Panda permissions. Either control axis can
remain active independently while its permission is valid.

The shared owner handles settings, gestures, transport, freshness and axis
arbitration. Vehicle adapters in `starpilot/car/<brand>/aol.py` own supported
CarParams, safety profiles and button assignments. `policy.py` defines the
contract; `vehicle.py` dispatches to registered adapters. Unknown or malformed
configurations receive no capability. Settings availability, intent admission
and ordinary runtime support are separate: a saved preference cannot grant
steering or longitudinal permission. Current adapters do not cover the entire
vehicle catalog.

Card publishes desired intent; SelfdriveD resolves the two desired axes; Controls
requires matching current native permission before actuating either axis.
Session changes, expired messages, invalid required CAN and the existing
actuator limits still apply. Lateral-only operation uses engaged driver
monitoring independently of the Always On DM preference.

Intent and axis messages have a 30 ms freshness bound; native acknowledgments
have a 200 ms bound. The host and pandad use the same monotonic clock. A new
session first negotiates an acknowledged zero-axis request. These checks are
independent of each vehicle's Panda safety policy.

`aolAxisState` uses custom slot 16. Intent and safety use reserved Data events 125
and 124 with bounded, versioned flat Cap'n Proto payloads. Mapd slots 17–19 remain
separate. Decode stored messages with their writing schema; never reinterpret
an incompatible cache or reuse an occupied event identifier. Upstream vehicle
schemas remain unchanged.

`AolBrakePauseSpeedMps` stores meters per second. If absent, `PauseAOLOnBrake`
retains its historical effective meters-per-second value, regardless of the old
UI label. An invalid threshold disables the additional AOL request without
rewriting the preference. Settings convert display units when writing the new
key. Invalid CAN or transfer of button ownership cancels an incomplete hold;
a deliberate axis pause remains latched until changed by the driver.

Common transport and arbitration tests live in `aol/tests`. Vehicle host tests
live in `selfdrive/car/tests`, and native safety tests in
`opendbc_repo/opendbc/safety/tests`. Keep new vehicle admission and its positive
and negative safety tests with the corresponding vehicle port.
