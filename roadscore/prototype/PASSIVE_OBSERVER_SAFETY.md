# Passive observer safety evidence

The helper accepts two exact observed variants with genuine `CarParams.passive`,
configured noOutput/parameter0, inactive fresh control/state signals and fault-free
pandas: all actual noOutput, or all actual ELM327/parameter1 under the documented
passive startup conditions. It is not authorization, calibration acceptance,
coexistence acceptance, engagement support, or proof of zero CAN traffic.

The earlier assumption that normal passive startup must reach actual noOutput was
incorrect. Source in `selfdrive/pandad/panda_safety.cc` initializes every panda to
ELM327 parameter1 before waiting for FirmwareQueryDone and ControlsReady. Upstream
`selfdrive/car/card.py` sets ControlsReady inside controls_update, while passive
step skips controls_update. Thus the normal passive path can remain in ELM327.
Parameter1 means no OBD multiplexing; enabling OBD multiplexing changes the primary
panda parameter to0. Only the explicit parameter1 baseline is accepted here.

The collector supplies current read-only `passive_startup` values:
`controls_ready=false`, `firmware_query_done=true`,
`obd_multiplexing_enabled=false`. Missing helper evidence fails closed; native
Params absent-bool semantics are the collector's responsibility. No helper writes
these flags or attempts to force a safety transition.

**ELM327 is not noOutput.** `opendbc/safety/modes/elm327.h` permits eight-byte
messages to diagnostic addresses 0x600–0x7FF, 0x18DB33F1, 0x18DAxxF1, and0x24B.
For0x24B it additionally restricts the leading ISO-TP nibble to0–3. Ordinary
allowed diagnostic addresses accept arbitrary payload content; this must not be
described as an all-TX-disabled safety mode. The mode uses nooutput_init and
requires observed controlsAllowed=false, but has its own diagnostic TX hook.
RoadScore's observer integration must continue to publish no CAN/control messages.

Faults remain an independent blocker, including interruptRateCan2. ELM allowance
does not waive safetyRxChecksInvalid, stale/invalid messages, active/always-on
lateral flags, calibration, model health, local-model placement, resource/link
bounds or parked coexistence. Mixed observed safety modes are rejected as a
transition/unestablished baseline. Mode identity includes actual ELM parameter1,
so a noOutput authorization pin cannot silently carry over to ELM.
