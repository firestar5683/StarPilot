# Palisade HDA2 consolidated review

Target: 2025 Hyundai Palisade Calligraphy HDA2, HYUNDAI_PALISADE_2023, comma 3X.
Base inspected: SecretGoodStarPilot 1a5ee718c92c309b61c33a1751aeeb84ad4285da.

## Included fixes

- Add the exact observed EPS and radar firmware response variants; unknown responses still fail exact matching.
- Select independent mapped LKAS/Main intent and remove the host cruise-main readiness dependency for the existing qualified HDA2 stock/alpha profiles only.
- Preserve the alpha intent factory's independent-button selection.
- Opt these Palisade HDA2 intent owners into observing a press followed by release in one CAN batch. The shared parser's default behavior remains unchanged for other owners.
- Schedule each fresh HDA2 camera-source suppression copy once, rather than using an unrelated controller-frame phase. Sender age includes parser age and subsequent controller delay; no native checksum, copy or freshness checks are changed.

No UI, sound, streaming, SLC, radar enablement, automatic launch or following-distance modifications are included. No native/Panda safety source or firmware artifacts are modified.

## Failed upstream drive

Route 00000032--6bf1cbce63 identifies its running commit as 71632a6b48374889bd8a95cf7e8b5fc2e78d0973. Recorded fingerprint was HYUNDAI_PALISADE_2023, alpha longitudinal enabled, alternativeExperience 32, Hyundai safety word 0x2014.

- Controls Mismatch takeovers: approximately 194.832, 221.492 and 230.245 seconds from route start.
- At 194.816 seconds, native lateral and longitudinal permission withdrew while both were requested; the following host publication withdrew commands and raised the mismatch warning. This is not evidence that the alert should be suppressed.
- At 327.476 seconds the parsed vehicle reported temporary steering unavailability, followed by accFaulted at 327.520 seconds and a Cruise Fault takeover near 327.526 seconds.
- No reported Panda relay faults or RX-check-invalid transitions in the route summary; maximum reported memory usage was 75%; no missing required processes were observed in the qlog scan.

These observations establish the reported failures, not their complete cause. The camera scheduling correction is a tested source-age/phase defect, not proof that it resolves all of these events.

## Validation

324 selected regressions passed in an isolated process using candidate Python modules against the preserved upstream 71632a6 runtime. Coverage includes exact firmware matching and unknown-response rejection, mapped button intent, marked/unmarked profiles, nearby-profile rejection, a coalesced LKAS pulse and consumed-button veto, fresh/old/duplicate camera scheduling and native-hook copy rejection, plus neighboring classic-family, CANFD stock and full-engagement intent tests.

The new independent-button suite initially reproduced six failures on unpatched upstream. Tests do not replace a complete latest-tree build, replay or vehicle validation. Candidate code has not been installed on the driving device.

## Open items for this same review

- Native alpha CANCEL currently clears its token. Host-only changes cannot guarantee pause/brake AOL retention when the native owner withdraws permission. The custom fork's different policy is intentionally not copied into this patch without a complete native/host review.
- The precise native permission withdrawal behind the three mismatch events and the cause of the reported ECU cruise fault remain unresolved.
- Reassess the old startup/ECU-disable workaround against upstream's newer initialization guard; this route did not reproduce the earlier relay/RX startup fault.
- The factory-owned 0x485 relay classification correction is already upstream and is not duplicated here.

This is one consolidated Palisade work-in-progress review. It must not be presented as complete support or a recommendation for other owners to engage the system yet.
