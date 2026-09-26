# Contributing to StarPilot

Start with the [project overview](../README.md), [build guide](how-to/laptop-device-build.md), and [developer commands](../tools/STARPILOT_DEVELOPMENT.md).

## Scope and behavior

Keep each change focused on one feature or defect. Describe the behavior before and after the change, the affected vehicle configurations or interfaces, and how it was verified. Preserve intentional StarPilot behavior and familiar controls unless the change explicitly proposes a different experience.

Prefer small integration points around upstream interfaces. Keep feature settings, state, and side effects with their owning feature. Shared code should express a real common contract, with regression coverage for the features that use it. Comments should explain an invariant, protocol requirement, or non-obvious decision.

## Interfaces and dependencies

Follow cereal's [custom-fork guidance](../openpilot/cereal/README.md#custom-forks). Preserve upstream message definitions and field meanings; put fork-specific messaging in the custom schema. Vehicle support outside an upstream platform's contract needs a distinct platform identity and corresponding interface and safety evidence.

Dependencies are tracked source folders. Use the [vendoring workflow](../tools/vendor/README.md), retain provenance and licenses, and review local changes when updating an upstream revision.

## Verification

Run checks appropriate to the change and describe the result in the pull request:

- For a bug fix, demonstrate the failure and the corrected behavior.
- For driving behavior, compare against the intended source behavior or recorded evidence and cover engagement, override, reset, and relevant limits.
- For vehicle or safety changes, identify the exact configuration and run the affected interface and native safety checks.
- For UI changes, inspect the affected interface at its actual size and preserve the intended interactions.
- For performance changes, provide a reproducible comparison and distinguish a component benchmark from whole-system performance.

Keep automated tests, bench observations, and driving results separate. State what remains unverified rather than broadening a narrow result into a fleet-wide claim.

## Commit history

Use concise feature or behavior names. Keep related changes together, including their tests and documentation. Preserve ordinary follow-up commits so contributors can follow changes.

The original [openpilot contribution guide](https://github.com/commaai/openpilot/blob/521db4c825d37eb5f29acf955daa88da003e4433/docs/CONTRIBUTING.md) documents upstream's process. Changes intended for comma's openpilot should follow that project's contribution requirements.
