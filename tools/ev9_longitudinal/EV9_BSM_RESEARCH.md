# EV9 blind-spot reconstruction research

## Corpus

The stock corpus currently contains 72 rlog segments from four independent routes, sampled at each native
`BLINDSPOTS_REAR_CORNERS` (`0x1BA`) update. The ADAS-suppressed availability corpus contains all 13 rlog
segments from route `00000109`.

| Route | Left episodes / positive time | Right episodes / positive time | Lamp-speed range |
|---|---:|---:|---:|
| `00000015` | 1 / 7.55 s | 0 / 0 s | left 28.44–29.08 m/s |
| `000000d4` | 21 / 165.90 s | 5 / 17.35 s | 4.33–29.14 m/s |
| `000000d5` | 0 / 0 s | 1 / 5.70 s | right 11.68–14.58 m/s |
| `000000d6` | 12 / 74.15 s | 19 / 88.25 s | 4.46–28.56 m/s |

The extractor now preserves every decoded `0x1BA` field, the complete raw 24-byte payload, car-state validity,
and per-address warmup/presence. This prevents synthetic zero-filled segment-boundary samples from being treated
as real vehicle or radar state.

## Native warning semantics

- `BCW_*IndSta == 1` is the normal solid detection state.
- Every observed `BCW_LtIndSta == 2` sample had the left blinker active. It is an escalated warning, not a
  different object class.
- During left state 2, the outside-mirror field `OSMrrLamp_LtIndSta` used state 2 for 16 samples and state 0 for
  four samples, confirming the observed 0.8 s on / 0.2 s off flash cadence at 20 Hz.
- Sound-warning state was pulsed rather than held through the complete escalation. The corpus has no right-side
  state-2 example yet.

## Retained-signal results

`0x36A SIDE_DETECT_STATE` remains the only side-specific signal that transfers across every applicable stock
route and also recurs after ADAS suppression. It is useful as late corroborating evidence, but it is not the
native rear-corner fusion decision.

| Route | Side | Raw `0x36A` frame P/R/F1 | Truth episodes hit | Median first-hit lag |
|---|---|---:|---:|---:|
| `00000015` | left | .684 / .358 / .470 | 1 / 1 | +4.85 s |
| `000000d4` | left | .181 / .236 / .205 | 17 / 21 | +4.05 s |
| `000000d6` | left | .148 / .176 / .161 | 11 / 12 | +4.29 s |
| `000000d4` | right | .209 / .236 / .222 | 4 / 5 | +2.70 s |
| `000000d5` | right | .235 / .237 / .236 | 1 / 1 | +4.35 s |
| `000000d6` | right | .212 / .328 / .257 | 14 / 19 | 0.00 s |

The clean `00000015` left episode is especially informative. Native BCW turns on 4.85 seconds before the left
`0x36A` bit. The standard decoded MRR side-region and camera-object side-region candidates never assert during
the episode. The current production-proxy left rule therefore has zero recall on this route.

An initial three-route scan found an apparent left correlate in MRR message `0x3AF`. The added `00000015`
holdout invalidated it: the bit never asserted during the new warning. This is why every proposed signal must be
judged on each route rather than on pooled frames.

## All-address and optimistic fusion limits

The all-address miner tests both polarities of every received CAN bit on each route and can require that its
message recur in the suppressed corpus. After adding `00000015`:

- No comma-visible, post-suppression bit reaches minimum per-route F1 above 0.21 for left detection.
- The best-ranked left bits are high-prevalence vehicle-state correlations with roughly 10–17% precision, not
  side-specific object evidence.
- The known right `0x36A` bit remains the strongest route-stable right correlate.
- `0x1BA`, `0x1E5`, `0x161`, `0x162`, and `0x1EA` have only ten boot frames in suppressed route `00000109` and
  are not deployable detection inputs. MRR35 and `0x36A` continue throughout that route.

An intentionally optimistic ExtraTrees test included raw CAN history, decoded camera objects, decoded MRR
objects, object-ID persistence, vehicle dynamics, and model/lane geometry. Its threshold was selected with
hindsight on each holdout, so the result is an upper bound rather than a deployable model. On new route
`00000015`, the best left result was only P=.227, R=.762, F1=.350. The other left holdouts were F1=.282 and
F1=.229. No holdout met 95% precision and 95% recall.

Forcing 100% frame recall makes the estimator nearly always-on. Optimistic holdout precision at 100% recall was
12.9%, 11.0%, and 7.3% on the three left-positive routes. Right precision was 2.1%, 74.0%, and 6.6%; the 74.0%
result is a single 5.7-second event in `000000d5` and does not transfer to either longer right-positive route.
Without the continuous model, an always-on 100%-recall baseline has only 5.9% pooled left precision and 2.7%
pooled right precision.

## Engineering conclusion

With the present bus access, a software estimator can provide low-confidence, usually late side-object evidence;
it cannot faithfully replace native BCW. Speed, steering angle/rate, persistence, and track geometry reduce
false positives, but they cannot recover warnings for vehicles never represented in the retained streams.

Keep all reconstructed mirror, vehicle, haptic, and comma BSM outputs disabled. Continue running the detector in
shadow mode and use `0x36A` as one scored input rather than authoritative truth. Faithful BSM requires access to
the native `0x1BA` decision or to the rear-corner sensor inputs used by ADAS fusion, such as through the split-bus
ADAS/eSCC hardware path.

## Reproduction

```bash
.venv/bin/python tools/ev9_longitudinal/extract_ev9_bsm_can_labels.py \
  --rlog-root /path/to/stock-rlogs --output /tmp/ev9_bsm_stock_extended.npz

.venv/bin/python tools/ev9_longitudinal/evaluate_ev9_bsm_heuristics.py \
  --npz /tmp/ev9_bsm_stock_extended.npz

.venv/bin/python tools/ev9_longitudinal/mine_ev9_bsm_can_correlations.py \
  --rlog-root /path/to/stock-rlogs \
  --availability-rlog-root /path/to/suppressed-rlogs
```

The next useful additions are independent stock routes containing right-side state-2 warnings, low-speed traffic,
reverse/cross-traffic scenes, and synchronized visual annotations of the actual adjacent vehicle.
