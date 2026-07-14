# EV9 BSM retained-signal fusion results

Analysis date: 2026-07-13

## Question and acceptance criterion

Can data that remains visible after the EV9 ADAS ECU's transmission is
suppressed reproduce the native `0x1BA` left and right BCW/BSM lamp decisions?

The required acceptance criterion is **at least 95% precision and 95% recall,
independently for each side, on a completely held-out route**. Overall accuracy
is not used because inactive samples dominate the corpus.

## Corpus and target

- 71 stock `rlog.zst` files, 82,780 aligned 0x1BA samples
- Routes: `000000d4` (26 segments), `000000d5` (22), `000000d6` (23)
- Native active samples: left 4,821; right 2,238
- Route counts:
  - d4: 30,339 rows, left 3,329, right 347
  - d5: 25,527 rows, left 0, right 114
  - d6: 26,914 rows, left 1,492, right 1,777

The target is the persistent native 0x1BA BCW indicator state. Training never
contains samples from the route used for evaluation.

## Object decode

The public Zendar front-camera DBC documents these object fields:

- quality, alive age, moving state, object ID, width, classification
- relative x/y, relative vx/vy, relative ax, sync index, absolute vx
- a nominal second object in the latter half of each 32-byte frame

The EV9 0x235--0x248 corpus has 20 first-object slots (0--12 valid in a sample,
median 4) and **zero valid second objects** across all 82,780 samples. Object
ID, age, and geometry are coherent enough for temporal association. Moving
values 10--15 also occur, outside the public DBC's documented 0--9 enumeration,
so their names are not assumed.

The source message names (`FR_CMR`) and unsigned forward x coordinate identify
this as front-camera object traffic. The DBC is field-layout provenance, not
proof that the camera output contains the EV9 rear-radar blind-zone inputs.

## Reproduction

```sh
# scikit-learn is analysis-only and is not part of the driving runtime.
.venv/bin/python -m pip install --target /tmp/ev9ml scikit-learn

.venv/bin/python tools/ev9_longitudinal/extract_ev9_bsm_can_labels.py \
  --rlog-root /Users/brenrid/Code/EV9-Route-References/stock-rlogs \
  --output /tmp/ev9_bsm_stock.npz

.venv/bin/python tools/ev9_longitudinal/extract_ev9_model_geometry.py \
  --can-npz /tmp/ev9_bsm_stock.npz \
  --rlog-root /Users/brenrid/Code/EV9-Route-References/stock-rlogs \
  --output /tmp/ev9_bsm_model_geometry.npz

PYTHONPATH=/tmp/ev9ml .venv/bin/python tools/ev9_longitudinal/analyze_ev9_bsm_fusion.py \
  --can-npz /tmp/ev9_bsm_stock.npz \
  --model-npz /tmp/ev9_bsm_model_geometry.npz \
  --trees 100

PYTHONPATH=/tmp/ev9ml .venv/bin/python tools/ev9_longitudinal/analyze_ev9_bsm_fusion.py \
  --can-npz /tmp/ev9_bsm_stock.npz \
  --model-npz /tmp/ev9_bsm_model_geometry.npz \
  --include-retained-raw --trees 80
```

The fusion features include slot-independent object sorting, spatial regions,
ID reassociation and persistence at 0.1--4 seconds, temporal snapshots through
5 seconds, vehicle kinematics/blinkers, model path/lane/road-edge geometry and
lane-change desire, plus optional retained MRR35/0x1E5/0x36A bytes. Temporal
maximum and mean holds from 0.3--2.0 seconds are evaluated.

## Input coverage limits

The failure is not only a classifier-selection problem:

- A maximally broad same-side 0x235 candidate covers only 91.33% of native
  right BSM frames. In 194 of 2,238 right-positive frames, the retained object
  list has no same-side candidate at all.
- Restricting candidates to plausible vehicle geometry/classification reduces
  right recall to 84.99% at 10.9% precision, and left recall to 90.91% at
  17.32% precision.
- One continuous 93-frame native right-BSM event contains a plausible
  same-side 0x235 object for only four frames. Another right event has no
  expected-side associated track.
- CCNC left side/rear slots reach only 17.1% precision and 23.9% recall against
  left BSM. Right side/rear slots have zero overlap with native right BSM at
  every tested lag from -10 to +10 seconds.

These hard coverage gaps prevent a 95%-recall detector regardless of model
capacity or threshold tuning.

## Strict route-holdout results

Best model-geometry fusion result on each eligible route:

| Side | Held route | Best F1 | Precision | Recall | Best P at R >= .95 | Best R at P >= .95 | 95/95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Left | d4 | .411 | .285 | .736 | .189 | .048 | No |
| Left | d6 | .211 | .185 | .247 | .088 | .015 | No |
| Right | d4 | .253 | .252 | .254 | .024 | .000 | No |
| Right | d5 | .835 | .717 | 1.000 | .722 | .000 | No |
| Right | d6 | .402 | .276 | .741 | .066 | .000 | No |

Adding retained raw MRR35/0x1E5/0x36A bytes did not generalize across routes:

| Side | Held route | Best F1 | Precision | Recall | Best P at R >= .95 | Best R at P >= .95 | 95/95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Left | d4 | .366 | .260 | .615 | .175 | .036 | No |
| Left | d6 | .191 | .107 | .874 | .086 | .013 | No |
| Right | d4 | .112 | .102 | .124 | .019 | .000 | No |
| Right | d5 | .884 | .810 | .974 | .810 | .316 | No |
| Right | d6 | .325 | .205 | .779 | .066 | .000 | No |

## Conclusion

No retained-signal rule or model approaches the 95%/95% requirement on either
side. Stable object IDs improve front/adjacent object association but do not
make the native rear blind-zone decision identifiable. The strong d5-right
result does not generalize to d4 or d6 and therefore is not safe evidence for a
production BSM policy.

A faithful implementation needs at least one of:

1. Preserve or safely relay the ADAS ECU's native 0x1BA BSM decision while
   suppressing only conflicting longitudinal messages.
2. Expose and decode the rear corner-radar object/status bus through the
   harness/network topology.
3. Capture an equivalent retained OEM decision signal proven across additional
   stock routes.

Until then, 0x235 objects can support a separately labeled HUD visualization,
but should not drive mirror BSM lamps as if they were the native safety warning.

## Primary references

- The 0x235 field layout was adapted by CarrotPilot from a public Zendar
  front-camera evaluation DBC; it is not an OEM EV9 rear-radar decode:
  [initial adaptation](https://github.com/ajouatom/openpilot/commit/36cd3a8f047b61782301909037c122f884f19b5e),
  [trimmed runtime fields](https://github.com/ajouatom/openpilot/commit/9222d79fb9140951ac4ca1e52c447d5dc9d979ee),
  [source DBC](https://github.com/ns896/python_codes/blob/82d7e5b02d13d75fe7d2d1d8073f9eb3e5aa5bda/CANFD_DataParser/dbc_file/20250404_CANFD_SV_Output_CANDB_ZENDAR_Evaluation_Project_v1.dbc).
- Native 0x1BA two-bit BCW semantics are validated in
  [commaai/opendbc PR 3296](https://github.com/commaai/opendbc/pull/3296).
- Kia documents the EV9 speed/target gates and signal-triggered audible and
  haptic escalation in the
  [official owner manual](https://www.kia.com/content/dam/kia2/in/en/content/ev9-manual/topics/t00683.html).
- Hyundai Mobis describes the relevant algorithm family—track persistence,
  fixed-object and guardrail suppression, and separate warning generation and
  keeping zones—in [US11769412B2](https://patents.google.com/patent/US11769412B2).
