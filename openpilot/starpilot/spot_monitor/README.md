# Visual adjacent-spot warnings

This package reconstructs V-ASM's image preparation, warning policy and optional
onroad producer. Its observations can select the existing native side-camera
PiP view. They never change OEM blindspot signals, lane-change eligibility or
vehicle controls, and do not qualify an adjacent lane as clear.

Version-1 polygon annotations use bounded source-frame pixel coordinates. The
decoder rejects malformed, empty, degenerate and self-intersecting contours.
There is no automatic adoption of an older annotation. Source pixels are
retained for a single float32 projection shared by the crop and mask; a lossy
normalized-coordinate round trip can otherwise shift an NV12 crop by two pixels.
The crop remains even-aligned and letterboxed to RGB NCHW `1×3×352×352`.

The CPU inference wrapper accepts an explicit external local model and verifies
its exact size and SHA-256 before constructing OpenCV's network from those
bytes. The loaded network keeps that identity until explicit reload; inference
does not reread the model file. Missing or changed assets, unavailable OpenCV,
invalid frames, and nonfinite or incorrectly shaped outputs return unavailable.

The reference artifact is 6,166,229 bytes with SHA-256
`5d20cdbb457ba18db51a537ee2e305bbe442264b1613956068d473e35d15900d`.
Its embedded metadata identifies Ultralytics and AGPL-3.0, with classes
`0_nocar`, `1_car`, and `2_distant_or_rear`. Weights are not bundled here;
artifact distribution and training-data provenance remain unresolved. Class 1
drives the visual-warning score. Default smoothing is 0.2 seconds, with 0.94/0.79
activation/release thresholds. Camera left maps to displayed right, preserving
the reference's orientation. Invalid or reversed timestamps reset warning
history, and each side expires after three seconds.

The manager requires device hardware, onroad state,
`STARPILOT_VASM_DEVELOPMENT=1`, an absolute external
`STARPILOT_VASM_MODEL_PATH`, and a valid enabled `VASMPreferences` document.
That strict version-1 document contains an explicitly configured annotation,
`enabled`, `confidence` (0.8–1.0) and `smoothSeconds` (0.01–0.5). Absent or
invalid settings leave the producer disabled without replacing saved bytes.

The producer consumes the existing cabin VisionIPC stream without starting a
camera. Fresh device state, valid CAN state and Drive gear are required. NV12
planes are copied with their actual stride and UV offset. A frame is admitted
only within 500 ms of its BOOTTIME end-of-frame timestamp; paired clocks detect
resume. Each side retains its original source and three-second warning expiry.
Settings and vehicle state are checked again after inference. Reconnect,
disablement, stale authority and resume clear the policy. Model-load failures
use a bounded retry interval. OpenCV runs one inference thread; the normal
one-second interval and 0.3-second follow-up slow down under CPU load.

The custom `spotMonitorState` event uses an upstream reserved type ID and Event
ordinal. Its historical `desiredCurvature @0` field keeps its original meaning
and is never written by this producer. The appended, versioned observation
contains model/settings identity, source times and per-side expiry. Old
curvature-only logs have observation version zero and cannot become warnings.
The service is sparse: consumers must check payload freshness, not rely on a
nominal publication frequency.

The native PiP consumer additionally requires its existing saved enablement
and `STARPILOT_PIP_DEV=1`. It uses the full event and validates source identity,
sessions, paired clocks and the current saved-settings fingerprint. Missing,
invalid or expired evidence clears the optional visual warning. Leaving onroad
or losing camera/vehicle state closes the subscription. Neither layout nor OEM
blindspot behavior changes.

Host checks cover geometry, input preparation, output handling, serialized
observation lifecycle and PiP selection. Synthetic classifier execution does
not establish real-scene accuracy, simultaneous device performance, calibration
or full feature parity. Weights remain external and no device activation is
implied by these checks.
