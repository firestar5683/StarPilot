# Short-startup controlled candidate

Normal launches retain the 100-second target. Only `ROADSCORE_TEST_SHORT_STARTUP=1` selects target 40 unless explicitly overridden. Whole accepted chunks quantize that to approximately **54 seconds** (26 + 28), not 40. At the reported current hardware timings (first accepted ~17 seconds, continuation 24.5–25.55 seconds), expected preparation is roughly **42–44 seconds**, compared with observed 91.0–91.3 seconds for 110 seconds of accepted audio. That estimate excludes launcher overhead and quality retries; it is not a measured short-startup result.

The per-session target is bounded (35–112 in explicit test mode, 80–112 otherwise), transmitted using resident protocol 2, validated before reset, acknowledged as actually applied, and checked against the completed bundle. No quality threshold, seed rule, reroll limit, deadline guard, or hold behavior is weakened. Old workers cannot apply a new target without **one owner-controlled restart after current playback**. Same-target old-worker launches remain compatible. An old worker requesting a different target fails before enqueue; echoing unknown fields cannot masquerade as applying the change.

`startup_buffer_audit.py` models 20 jobs alternating the supplied 24.5/25.55-second observations, adding 28 seconds accepted music per success. Guard starts at 40 seconds, updates to max(30, observed*1.2)+10, request threshold remains90, accepted-tail hold adds24 seconds. The adverse sequence begins with rejected23-second work followed by a26-second retry if its original deadline permits. This is a **sensitivity simulation**, not a replay of complete hardware trace timestamps.

| Initial actual reserve | All accepted: minimum / holds | Early rejected job: minimum / holds / fresh jobs |
|---|---|---|
|82 seconds|57.50 / 0|33.00 / 0 / 20|
|54 seconds (40 target)|29.50 / 0|29.45 / 1 / 19|
|40 seconds hypothetical|20.00 / 1|20.00 / 2 / 19|
|30 seconds hypothetical|29.50 / 1|29.45 / 2 / 19|

All simulated underflow counts are zero **only under instantaneous viable holds and zero callback/scheduling jitter**. These are not hardware underflow predictions. The54-second case cannot admit the early second quality attempt inside the original deadline: it keeps accepted music through a reported hold, then resumes fresh work.30 seconds is deliberately not an allowed target. The existing adaptive GenerationBudget and inflight20-second hold reserve remain unchanged.

The last supplied real long-run evidence was20 jobs, no retries, minimum64 seconds. A newer observed rejection plus retry took49 seconds. These motivate measuring holds and minimum buffer during the controlled short-startup test; the prior no-retry64-second minimum is not proof the smaller reserve is safe.

## Additional launcher time

Source inspection finds no fixed26–34-second sleep. `normal_onroad.py` sequentially seeds route params/acquires display before starting the receiver; `native_receiver.sh` then runs manifest capture and app initialization after preparation, with at most roughly two1-second polling delays plus bridge subscription. In `app.py`, full-source `analyze_music` and full-source `assess_grid` run before `RhythmTimeline.add` assesses overlapping windows again; the standalone grid is immediately replaced by `timeline.at(0)`. Removing that duplicate while preserving required audit fields is a clear candidate. Actual stage timestamps or a labeled offline profile are required to assign the26–34 seconds quantitatively. No app or launcher edit is included here.
