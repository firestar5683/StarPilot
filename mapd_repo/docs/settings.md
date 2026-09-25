# Settings
Mapd settings are stored in the MapdSettings param. They can be directly
controlled through the param or through MapdIn cereal messages. See inputs.md
for more details about loading and saving settings. The following is details
about each setting, including location in the MapdSettings param and their
corresponding MapdIn actions.

## Settings Version and Schema
The MapdSettings param (and the custom defaults/recommended json files
described in overriding-internal-defaults.md) are versioned with a
`settings_version` field, currently `2`. As of version 2 the settings are
grouped into nested objects (`subscriber`, `speed_limit`, `logger`,
`personalities`) instead of one flat object. Param Key values below use dot
notation to show the full path within that nested structure, e.g.
`speed_limit.speed_limit_offset` means `{"speed_limit": {"speed_limit_offset":
...}}`.

If mapd loads a param or custom json file with an older `settings_version` it
automatically migrates it to the current version before use, so existing v1
settings continue to work without manual changes. New custom defaults/
recommended files should be written directly in the v2 shape documented here.

## Setting Values Through MapdIn
Most settings can be set with the generic `setJsonPathBool`,
`setJsonPathFloat`, and `setJsonPathText` MapdIn types: put the setting's
Param Key (the dot path) in the `jsonPath` field and the value in the
matching `bool`/`float`/`str` field.

A number of dedicated MapdIn types from before settings v2 (e.g.
`setSpeedLimitOffset`, `setTargetSpeedJerk`, `setLogLevel`) still work and are
listed as deprecated below where applicable. Where a dedicated type touches a
value that is now personality-specific (jerk, accel, lat A, time offsets,
next-speed-limit behavior), it sets that value for all three personalities at
once rather than one at a time.

### Settings Version
The schema version of the settings. Mapd migrates older versions to the
current schema on load; this should not normally be set directly.

| Item      | Description |
| --------- | ----------- |
| Param Key | settings\_version |

### Speed Limit Control Enabled
When enabled mapd will use the speed limit to determine a suggested speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit\_control\_enabled) |
| MapdIn Type (deprecated) | setSpeedLimitControl |
| MapdIn Field | bool |
| Param Key    | speed\_limit\_control\_enabled |

### Map Curve Speed Control Enabled
When enabled mapd will use map based curvature calculations to determine a suggested speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: map\_curve\_speed\_control\_enabled) |
| MapdIn Type (deprecated) | setMapCurveSpeedControl |
| MapdIn Field | bool |
| Param Key    | map\_curve\_speed\_control\_enabled |

### Vision Curve Speed Control Enabled
When enabled mapd will use vision model based curvature calculations to determine a suggested speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: vision\_curve\_speed\_control\_enabled) |
| MapdIn Type (deprecated) | setVisionCurveSpeedControl |
| MapdIn Field | bool |
| Param Key    | vision\_curve\_speed\_control\_enabled |

### Conditional Speed Limit Control Enabled
When enabled mapd applies conditional speed limits (the osm maxspeed:conditional
tag) to the speed limit when their condition currently applies. Only simple
day/time conditions are evaluated (e.g. `25 mph @ (Mo-Fr 07:00-17:00)` school
zones or `100 @ (22:00-06:00)` night limits); conditions mapd can't fully
evaluate (weather, public holidays, months, vehicle class) are ignored and the
regular speed limit is used. Conditions are checked against the device's local
time, so the device timezone must be correct. The raw tag is always output in
mapdOut regardless of this setting so forks can do their own handling.

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setConditionalSpeedLimitControl |
| MapdIn Field | bool |
| Param Key    | conditional\_speed\_limit\_control\_enabled |

### External Speed Limit Control Enabled
When enabled mapd will use fork provided speed limits to determine a suggested speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: external\_speed\_limit\_control\_enabled) |
| MapdIn Type (deprecated) | setExternalSpeedLimitControl |
| MapdIn Field | bool |
| Param Key    | external\_speed\_limit\_control\_enabled |

### Mapd Enable Speed
The speed you can set your cruise control to that will then cause mapd features to engage

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: enable\_speed) |
| MapdIn Type (deprecated) | setEnableSpeed |
| MapdIn Field | float |
| Units        | meters/second |
| Param Key    | enable\_speed |

### Use Enable Speed For Speed Limit
Determines whether the Mapd Enable Speed controls enabling of Speed Limit Control

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit\_use\_enable\_speed) |
| MapdIn Type (deprecated) | setSpeedLimitUseEnableSpeed |
| MapdIn Field | bool |
| Param Key    | speed\_limit\_use\_enable\_speed |

### Use Enable Speed for Map Curve Speed Control
Determines whether the Mapd Enable Speed controls enabling of Curve Speed Control

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: map\_curve\_use\_enable\_speed) |
| MapdIn Type (deprecated) | setMapCurveUseEnableSpeed |
| MapdIn Field | bool |
| Param Key    | map\_curve\_use\_enable\_speed |

### Use Enable Speed for Vision Curve Speed Control
Determines whether the Mapd Enable Speed controls enabling of Vision Curve Speed Control

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: vision\_curve\_use\_enable\_speed) |
| MapdIn Type (deprecated) | setVisionCurveUseEnableSpeed |
| MapdIn Field | bool |
| Param Key    | vision\_curve\_use\_enable\_speed |

### Default Lane Width
The default lane width to use when determining if we are currently on a road

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: default\_lane\_width) |
| MapdIn Type (deprecated) | setDefaultLaneWidth |
| MapdIn Field | float |
| Units        | meters |
| Param Key    | default\_lane\_width |

## Speed Limit Settings (`speed_limit`)
These settings live under the `speed_limit` object in the MapdSettings param.

### Speed Limit Priority
Sets the prioritization method for available speed limits

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathText (jsonPath: speed\_limit.speed\_limit\_priority) |
| MapdIn Type (deprecated) | setSpeedLimitPriority |
| MapdIn Field | str |
| Values       | map, external, highest, lowest |
| Param Key    | speed\_limit.speed\_limit\_priority |

### Speed Limit Offset
The offset that gets applied to a speed limit to determine a target speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: speed\_limit.speed\_limit\_offset) |
| MapdIn Type (deprecated) | setSpeedLimitOffset |
| MapdIn Field | float |
| Units        | meters/second |
| Param Key    | speed\_limit.speed\_limit\_offset |

### Speed Limit Change Requires Accept
Requires user acceptance of any speed limit changes before activating

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.speed\_limit\_change\_requires\_accept) |
| MapdIn Type (deprecated) | setSpeedLimitChangeRequiresAccept |
| MapdIn Field | bool |
| Param Key    | speed\_limit.speed\_limit\_change\_requires\_accept |

### Press Gas To Accept Speed Limit
Pressing the gas will accept a speed limit change

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.press\_gas\_to\_accept\_speed\_limit) |
| MapdIn Type (deprecated) | setPressGasToAcceptSpeedLimit |
| MapdIn Field | bool |
| Param Key    | speed\_limit.press\_gas\_to\_accept\_speed\_limit |

### Press Gas To Override Speed Limit
Pressing the gas will override the speed limit to hold the current speed. Resets when the speed limit changes

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.press\_gas\_to\_override\_speed\_limit) |
| MapdIn Type (deprecated) | setPressGasToOverrideSpeedLimit |
| MapdIn Field | bool |
| Param Key    | speed\_limit.press\_gas\_to\_override\_speed\_limit |

### Adjust Set Speed To Accept Speed Limit
Adjusting the set speed once in either direction will accept a speed limit change. Additional set speed changes reject the speed limit

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.adjust\_set\_speed\_to\_accept\_speed\_limit) |
| MapdIn Type (deprecated) | setAdjustSetSpeedToAcceptSpeedLimit |
| MapdIn Field | bool |
| Param Key    | speed\_limit.adjust\_set\_speed\_to\_accept\_speed\_limit |

### Accept Speed Limit Timeout
The amount of time after a speed limit change is detected that accept inputs will be used. 0 is no limit

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: speed\_limit.accept\_speed\_limit\_timeout) |
| MapdIn Type (deprecated) | setAcceptSpeedLimitTimeout |
| MapdIn Field | float |
| Units        | seconds |
| Param Key    | speed\_limit.accept\_speed\_limit\_timeout |

### Hold Speed Limit While Changing Set Speed
When enabled mapd will suggest using the speed limit while the cruise control speed is changing. This prevents speeding up while trying to reach the enable speed

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.hold\_speed\_limit\_while\_changing\_set\_speed) |
| MapdIn Type (deprecated) | setHoldSpeedLimitWhileChangingSetSpeed |
| MapdIn Field | bool |
| Param Key    | speed\_limit.hold\_speed\_limit\_while\_changing\_set\_speed |

### Hold Last Seen Speed Limit
When enabled mapd will use the last seen speed limit if it cannot determine a current speed limit

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: speed\_limit.hold\_last\_seen\_speed\_limit) |
| MapdIn Type (deprecated) | setHoldLastSeenSpeedLimit |
| MapdIn Field | bool |
| Param Key    | speed\_limit.hold\_last\_seen\_speed\_limit |

## Personalities (`personalities`)
Mapd computes speed change activation distances and curve/speed-limit targets
using one of three tunable profiles: `relaxed`, `standard`, or `aggressive`.
Mapd subscribes to openpilot's `selfdriveState` message and reads
`selfdriveState.personality` (openpilot's longitudinal personality, set by the
user through openpilot's own UI/controls) every tick to pick which profile is
currently active; `standard` is used as the fallback when no valid value has
been read yet. All three profiles are configured independently in the
MapdSettings param under `personalities.relaxed`, `personalities.standard`,
and `personalities.aggressive`.

There is no dedicated per-personality MapdIn type — set these values with
`setJsonPathFloat`/`setJsonPathBool` using a `jsonPath` of the form
`personalities.<relaxed|standard|aggressive>.<field>`, e.g.
`personalities.aggressive.target_speed_jerk`. The deprecated non-path MapdIn
types below (carried over from before personalities existed) set the same
field on all three personalities at once.

### Target Speed Jerk
The target amount of jerk to use when determining speed change activation distance (map curve and speed limit)

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.target\_speed\_jerk) |
| MapdIn Type (deprecated, sets all personalities) | setTargetSpeedJerk |
| MapdIn Field | float |
| Units        | meters/second^3 |
| Param Key    | personalities.\<name\>.target\_speed\_jerk |

### Target Speed Accel
The target amount of acceleration to use when determining speed change activation distance (map curve and speed limit)

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.target\_speed\_accel) |
| MapdIn Type (deprecated, sets all personalities) | setTargetSpeedAccel |
| MapdIn Field | float |
| Units        | meters/second^2 |
| Param Key    | personalities.\<name\>.target\_speed\_accel |

### Curve Target Speed Time Offset
An offset for the time before a target position to reach the target speed (map curve)

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.curve\_target\_speed\_time\_offset) |
| MapdIn Field | float |
| Units        | seconds |
| Param Key    | personalities.\<name\>.curve\_target\_speed\_time\_offset |

### Speed Limit Increase Target Speed Time Offset
An offset for the time before a target position to reach the target speed (speed limit, when the upcoming limit is higher than the current one)

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.speed\_limit\_increase\_target\_speed\_time\_offset) |
| MapdIn Field | float |
| Units        | seconds |
| Param Key    | personalities.\<name\>.speed\_limit\_increase\_target\_speed\_time\_offset |

### Speed Limit Decrease Target Speed Time Offset
An offset for the time before a target position to reach the target speed (speed limit, when the upcoming limit is lower than the current one)

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.speed\_limit\_decrease\_target\_speed\_time\_offset) |
| MapdIn Field | float |
| Units        | seconds |
| Param Key    | personalities.\<name\>.speed\_limit\_decrease\_target\_speed\_time\_offset |

### Target Speed Time Offset (Deprecated)
Sets Curve Target Speed Time Offset, Speed Limit Increase Target Speed Time Offset, and Speed Limit Decrease Target Speed Time Offset to the same value for all three personalities. Kept for backwards compatibility; new integrations should set the settings above independently.

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setTargetSpeedTimeOffset |
| MapdIn Field | float |
| Units        | seconds |

### Map Curve Target Lateral Acceleration
The maximum lateral acceleration used in the Map Curve Control speed calculations

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.map\_curve\_target\_lat\_a) |
| MapdIn Type (deprecated, sets all personalities) | setMapCurveTargetLatA |
| MapdIn Field | float |
| Units        | meters/second^2 |
| Param Key    | personalities.\<name\>.map\_curve\_target\_lat\_a |

### Vision Target Lateral Acceleration
The maximum lateral acceleration used in the Vision Curve Control speed calculations

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.vision\_curve\_target\_lat\_a) |
| MapdIn Type (deprecated, sets all personalities) | setVisionCurveTargetLatA |
| MapdIn Field | float |
| Units        | meters/second^2 |
| Param Key    | personalities.\<name\>.vision\_curve\_target\_lat\_a |

### Vision Minimum Target Velocity
The minimum speed that Vision Curve Control will request to drive

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathFloat (jsonPath: personalities.\<name\>.vision\_curve\_min\_target\_v) |
| MapdIn Type (deprecated, sets all personalities) | setVisionCurveMinTargetV |
| MapdIn Field | float |
| Units        | meters/second |
| Param Key    | personalities.\<name\>.vision\_curve\_min\_target\_v |

### Slow Down For Next Speed Limit
Determines if mapd will try to meet the upcoming speed limit before reaching it when the upcoming speed limit is lower than the current limit

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: personalities.\<name\>.slow\_down\_for\_next\_speed\_limit) |
| MapdIn Type (deprecated, sets all personalities) | setSlowDownForNextSpeedLimit |
| MapdIn Field | bool |
| Param Key    | personalities.\<name\>.slow\_down\_for\_next\_speed\_limit |

### Speed Up For Next Speed Limit
Determines if mapd will try to meet the upcoming speed limit before reaching it when the upcoming speed limit is higher than the current limit

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: personalities.\<name\>.speed\_up\_for\_next\_speed\_limit) |
| MapdIn Type (deprecated, sets all personalities) | setSpeedUpForNextSpeedLimit |
| MapdIn Field | bool |
| Param Key    | personalities.\<name\>.speed\_up\_for\_next\_speed\_limit |

## Subscriber Settings (`subscriber`)
Openpilot has a limited number of msgq subscriber slots. mapd normally
shadows only the `carState` subscriber (piggybacking on an existing
subscription rather than opening a new one) since stock openpilot uses nearly
every slot. These settings let a fork shadow additional subscribers instead
of opening new ones if it runs into subscriber slot exhaustion, at the cost of
sharing that subscription's read cursor with whatever else shadows it.
**Restarting mapd is required for changes to these settings to take effect**,
since subscribers are only created at startup.

### Shadow Car State
Shadow the carState subscriber instead of opening a dedicated one

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: subscriber.shadow\_car\_state) |
| MapdIn Type (deprecated) | setShadowCarState |
| MapdIn Field | bool |
| Param Key    | subscriber.shadow\_car\_state |

### Shadow Model V2
Shadow the modelV2 subscriber instead of opening a dedicated one

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: subscriber.shadow\_model\_v2) |
| MapdIn Type (deprecated) | setShadowModelV2 |
| MapdIn Field | bool |
| Param Key    | subscriber.shadow\_model\_v2 |

### Shadow GPS Location
Shadow the gpsLocation subscriber instead of opening a dedicated one

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: subscriber.shadow\_gps\_location) |
| MapdIn Type (deprecated) | setShadowGpsLocation |
| MapdIn Field | bool |
| Param Key    | subscriber.shadow\_gps\_location |

### Shadow GPS Location External
Shadow the gpsLocationExternal subscriber instead of opening a dedicated one

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: subscriber.shadow\_gps\_location\_external) |
| MapdIn Type (deprecated) | setShadowGpsLocationExternal |
| MapdIn Field | bool |
| Param Key    | subscriber.shadow\_gps\_location\_external |

### Shadow Selfdrive State
Shadow the selfdriveState subscriber instead of opening a dedicated one. There
is no dedicated MapdIn type for this setting; use setJsonPathBool.

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: subscriber.shadow\_selfdrive\_state) |
| MapdIn Field | bool |
| Param Key    | subscriber.shadow\_selfdrive\_state |

## Logger Settings (`logger`)
These settings live under the `logger` object in the MapdSettings param.

### Log Level
Modify how verbose logging will be for the mapd system

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathText (jsonPath: logger.log\_level) |
| MapdIn Type (deprecated) | setLogLevel |
| MapdIn Field | str |
| Values       | error, warn, info, debug |
| Param Key    | logger.log\_level |

### Use JSON Logger
When true the logs will be output in a json format instead of a text format

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: logger.log\_json) |
| MapdIn Type (deprecated) | setLogJson |
| MapdIn Field | bool |
| Param Key    | logger.log\_json |

### Log Source Location
When true the logs will include the file and line that wrote the log

| Item         | Description |
| ------------ | ----------- |
| MapdIn Type  | setJsonPathBool (jsonPath: logger.log\_source) |
| MapdIn Type (deprecated) | setLogSource |
| MapdIn Field | bool |
| Param Key    | logger.log\_source |
