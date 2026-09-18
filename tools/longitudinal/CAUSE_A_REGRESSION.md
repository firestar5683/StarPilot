# Cause A longitudinal regression

This branch contains a **diagnostic/replay harness only**. It does not change vehicle behavior.

## Positive regression set

- T0004
- T0008
- T0063
- T0064
- T0084
- T0132

The expected Cause A signature is a model `gasPressProb[1]` low enough to close
`model_allow_throttle`, followed by an acceleration target clamped near the
physical coast acceleration despite a more-positive longitudinal request, with
no lead/stop/brake/StarPilot disable reason explaining the clamp.

## Build the dataset

From a StarPilot checkout on the Windows machine that contains the extracted
logs:

```powershell
python .\tools\longitudinal\cause_a_regression.py --output-root D:\OpenPilot\Output
```

If checkpoint-02 episode IDs are stored somewhere else:

```powershell
python .\tools\longitudinal\cause_a_regression.py `
  --output-root D:\OpenPilot\Output `
  --episodes-csv D:\OpenPilot\Output\Analysis\ThrottleScan\checkpoint02_candidates_full.csv
```

The tool does not edit source logs.

## Outputs

By default:

```text
D:\OpenPilot\Output\Regression\A\
  manifest.csv
  manifest.json
  criteria.json
  variant_summary.csv
  global_variant_impact.csv
  global_variant_summary.json
  redlight_cross_tab.json
  summary.txt
  T0004\timeline.csv
  T0008\timeline.csv
  T0063\timeline.csv
  T0064\timeline.csv
  T0084\timeline.csv
  T0132\timeline.csv
```

Exit code 0 means all six IDs were resolved. Exit code 2 means at least one
episode could not be resolved and should not be silently substituted.

## Policies evaluated

The harness compares:

- `baseline_250ms`: current StarPilot confirmation time.
- `confirm_500ms`: same semantics, longer confirmation.
- `confirm_750ms`: same semantics, still longer confirmation.
- `context_bypass_250ms`: experimental diagnostic policy that bypasses the
  model gate only for clean below-target positive-demand frames.

No policy is selected merely because it fixes the six positive cases.

The global impact files also replay every checkpoint episode available in the
episode table and classify non-positive controls, including explicit StarPilot
gates and lead/stop/brake contexts. They quantify how much each candidate would
change gate-closed duration outside Dataset A.

## Regression criteria

A selected patch must:

1. Reproduce the Cause A baseline signature on every resolved positive case.
2. Reduce `clean_false_coast_seconds` versus baseline on every Cause A case.
3. Preserve explicit `disableThrottle`, driver-brake, lead, stop,
   `forcingStop`, red-light, and physical acceleration/deceleration safeguards.
4. Pass negative-control testing before any vehicle test.

The positive dataset is therefore necessary but not sufficient for choosing a
final patch.


## Red-light confounder check

The original checkpoint-02 scanner did not exclude `starpilotPlan.redLight`
when selecting suspicious model-gate episodes. The regression harness therefore
reports two signatures:

- `core_signature_pass`: low model gas probability + coast-clamped target +
  positive-demand context with no brake/lead/forcingStop/disableThrottle cause.
- `baseline_signature_pass`: the strict form above with `redLight=False`.
- `redlight_confounded`: the core signature is present but the episode is
  dominated by `redLight=True`.

`redlight_cross_tab.json` measures this relationship across every extracted
active timeline frame. A patch to the throttle gate must not be selected until
this confounder is resolved, since delaying throttle suppression during a true
stop-light approach could be unsafe.
