# Lateral controller regression vectors

These source-derived vectors are inputs to `test_ioniq6_policy.py`.

- `ioniq6_frozen_2023.json` and `ioniq6_frozen_2025.json` cover the two Ioniq 6 controller variants through stop, crawl, pull-away, highway, steering override, and restart. They include controller output, requested lateral acceleration and jerk, PID terms, and feedforward. Their `helpers` entries cover the corresponding shaping functions.
- `non_ioniq_parent.json` checks that Corolla TSS2 and Ioniq 5 controller output remains unchanged by the Ioniq-specific policy.

The tests use matching vehicle parameters for each comparison. These vectors check software behavior; they do not establish physical steering performance.
