# Source provenance

## MRR35 Hyundai angle and radar

The four MRR35 angle platforms (2026 Genesis GV70, second-generation electrified GV70, 2025 Genesis GV80, and Hyundai Ioniq 9) adapt Hyundai CAN FD angle-control design and the MRR35 radar DBC generator from the locally frozen StarPilot source snapshot `678af783`. That snapshot traces its Hyundai extension work to sunnypilot/opendbc `hkg-angle-steering-2025` at `cc4b08625a98e94b318cab15e45e05dad58042bd`; its historical import revision is not established. The relevant upstream contributors include Haibin (Jason) Wen, Shane Smiskol, and DevTekVE. Their authorship remains attributable to the upstream history; they do not maintain or endorse this port.

The copied MRR35 generator source and DBC definition are at `opendbc_repo/opendbc/dbc/generator/hyundai/hyundai_mrr35_radar.py` and `.dbc`. The host angle adapter and native safety profile are adaptations, not copies of a generic DBC or of unrelated vehicle support. Applicable upstream notices are preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Ford support adapted from BluePilot

The Ford lateral strategies, extended CAN constructors and native checks are adapted from StarPilot `2efe6017bfe14cee4807833e05f9a7f6ba255cdb`. Their lineage includes BluePilot's `bp-7.0` Ford work, principally by Alan Polk, with contributions from John Christman, Jacob Neulight, tonesto7, Haibin Wen and other sunnypilot and BluePilot contributors. The reference snapshot is [`e1d051d7ba270261b4455068bd68f1a58db15a4a`](https://github.com/BluePilotDev/bluepilot/commit/e1d051d7ba270261b4455068bd68f1a58db15a4a); the exact checkout used for the earlier StarPilot import was not recorded.

Relevant lineage includes the controller and integration work in [`db2bdff05`](https://github.com/BluePilotDev/bluepilot/commit/db2bdff05df103d71df62f45c2a3cb5211aba6e6) and [`d0aac605f`](https://github.com/BluePilotDev/bluepilot/commit/d0aac605f99d37e9da205e419f7989c1e9eaa386), extended CAN and safety work in [`8f8d6d15f`](https://github.com/BluePilotDev/bluepilot/commit/8f8d6d15f0a590f42b78de964ffb0d0af7f5d63d), and manual-turn detection in [`97867c1eb`](https://github.com/BluePilotDev/bluepilot/commit/97867c1eb57b7472f6fc3de62f0fef576e5a5497).

The vehicle strategy and CAN/native owners preserve that attribution while adapting to the current controller interfaces and shared safety limits. Upstream contributors do not maintain or endorse this adaptation. Applicable notices are retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
