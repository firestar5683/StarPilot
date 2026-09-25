# BluePilot angle source

Adapted from BluePilotDev/bluepilot bp-7.0 at
[e1d051d7ba270261b4455068bd68f1a58db15a4a](https://github.com/BluePilotDev/bluepilot/commit/e1d051d7ba270261b4455068bd68f1a58db15a4a),
principally Alan Polk, with John Christman, Jacob Neulight, Nathan Ingraham,
Praeuner, tonesto7, Haibin Wen and other BluePilot, sunnypilot and comma contributors.
Source paths: opendbc/sunnypilot/car/ford/lateral_angle_ext.py,
fordcan_ext.py, human_turn.py and opendbc/safety/modes/ford.h.
The simultaneous upstream LICENSE and LICENSE.md notices are retained.
This software is licensed under a custom license requiring permission for use.
This project uses software from Haibin Wen and SUNNYPILOT LLC and is licensed under a custom license requiring permission for use.

This is a StarPilot adapter to the September 2026 proposed library shape.
It is not a released BluePilot library, tag, or claim of BluePilot validation.
The existing curvature controller remains StarPilot-owned. Pinion curvature,
curvature-primary settings and the unsafe native reset bypass are not imported.

The exact upstream root notices are additionally retained as upstream-root-LICENSE
and upstream-root-LICENSE.md; LICENSE/ LICENSE.md retain the opendbc notices.
ORIGIN_HISTORY.tsv records the inspected path history with commit IDs/authors/dates.
The private compact upstream root clone preserves its reachable root history.
Pre-conversion opendbc submodule objects are not included in that root history.

Angle lane-centering trim is separately adapted from BluePilot bp-dev
[e22afa6be9b881fa784c92ebb316db47728a3d81](https://github.com/BluePilotDev/bluepilot/commit/e22afa6be9b881fa784c92ebb316db47728a3d81),
`opendbc/sunnypilot/car/ford/lane_center_trim.py` (blob
`5eedebd79e99493624f9d6af0750d1dd5713306c`). Alan Polk authored the initial
trim, model-position fallback, correction slew and default-strength changes;
ghbarker contributed reference/NaN guards and tests. The source explicitly credits
StarPilot/u/jc01rho for curvature-domain placement/geometry. The core adaptation
adds immutable host projection and conservative stale/driver-pressure suppression.
The pinned bp-7.0 controller baseline and default-disabled policy are unchanged.
Both simultaneous root/opendbc MIT and Custom MIT notices also exist unchanged at
this trim revision; all retained notices and permission acknowledgments apply
without assigning an exclusive license or claiming a new permission grant.
