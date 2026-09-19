# Controlled gold-core rendering comparison

Opt in on a fresh ACE run with `./onroad ... --composer ace --render-mode gold-core`.
The existing default is `current`. Stored replay rejects gold-core because an
already-rendered archive cannot be unmixed by this switch.

ACE worker files already carry the original 0.65 output gain. Gold-core passes
the assembled PCM to output at unity: no EventDSP/DrivingDSP/MusicalDSP, gesture
bank, arrival fade/cadence, or post-arrival source-zeroing. The recorder's dry
and heard streams therefore contain the same samples. There is no additional
processing or comparison renderer in the audio callback. A processed comparison
can be reconstructed offline from the saved same-generation source and events.

The generation, qualification, continuation, scheduling, accepted-audio holds,
causal input clock and replay EOF remain unchanged. This isolates rendering; it
does not claim the extended composition matches a standalone 28-second gold
initial. The experimental section bank is rejected, as is non-ACE use.

The selected mode is recorded in launcher settings/launch, runtime manifest,
and status/trace. The manifest hashes the rendering policy implementation.
Gold-core suppresses gesture activation displays because those gestures are
not played. Preserve original archives and indices before a controlled test.

Native deployment and a fresh test require the integration owner's review.
No resident-session, Galaxy, live-input or new engagement DSP is included.
