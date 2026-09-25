# Outputs

Mapd outputs data using two different cereal messages. MapdOut is the primary
output of mapd and is output at a rate of 20 hz. MapdExtendedOut contains data
that is needed in less realtime and thus is output at a rate of 1hz.

## MapdOut
Contains the primary outputs of mapd used during driving.

Output Frequency: 20hz
Queue Size: MEDIUM (2mb)

Suggested openpilot cereal settings:
Frequency: 20
Should Log: True
Decimation: 20

### Values
* **suggestedSpeed**: This is the primary value to use as the speed in
openpilot. It takes into account all mapd settings and data to give a target max
speed for openpilot.
* **wayName**: The name tag for the openstreetmap way that we are currently on.
* **wayRef**: The ref tag for the openstreetmap way that we are currently on.
* **roadName**: The suggested name to show for a road. It's just the wayName
with a fallback to wayRef when wayName is blank.
* **speedLimit**: The speed limit from the openstreetmap way that we are
currently on. It takes into account direction of travel, so if there is forward
or backwards max speed tag on osm this value will automatically use it based on
the direction of travel. When conditional speed limit control is enabled and a
parseable day/time condition from the way's maxspeed:conditional tag currently
applies, this value reflects the conditional limit instead.
* **conditionalSpeedLimit**: The raw maxspeed:conditional tag text for the way
we are currently on (direction of travel taken into account, like speedLimit).
Always output when the tag is present so forks can evaluate conditions mapd
does not handle itself (weather, vehicle class, ...). Empty when the way has no
conditional tag or the loaded map tiles predate this field.
* **nextSpeedLimit**: The next speed limit change that we see on the predicted path. This value also takes direction of travel into consideration.
* **nextSpeedLimitDistance**: The approximate distance to the next speed limit
change that we see on the predicted path.
* **hazard**: The hazard tag for the openstreetmap way that we are currently on.
* **nextHazard**: The next hazard change that we see on the predicted path.
* **nextHazardDistance**: The distance to the next hazard we see on the
predicted path.
* **advisorySpeed**: The maxspeed:advisory tag for the openstreetmap way we are
  currently on. This is typically used for the yellow speed signs at curves (in
the US).
* **nextAdvisorySpeed**: The next advisory speed change that we see on the
predicted path.
* **nextAdvisorySpeedDistance**: The distance to the next advisory speed change
  that we see on the predicted path.
* **oneWay**: Indicates if the openstreetmap way we are currently on is marked
as a one way road.
* **lanes**: The number of lanes from the openstreetmap way we are currently on.
* **tileLoaded**: Indicates if we successfully loaded a mapd data tile for the
current location.
* **speedLimitSuggestedSpeed**: This is the suggested speed to use based on
speed limit plus offsets and takes into account the speed limit priority. This
is primarily what's used to decide if the current speed limit is accepted or
not.
* **estimatedRoadWidth**: The width in meters that mapd used for determining
whether we were on the current road. Based off of the lanes value multiplied by
the lane width setting.
* **roadContext**: freeway, city, unknown. The type of road we decided to use
for the current road when determining which road we are on.
* **highwayClass**: The OSM highway tag value of the way we are currently on
(motorway, motorwayLink, trunk, ..., residential, livingStreet). Unlike
roadContext this is not inferred, it is the actual classification from
openstreetmap, so it can for example distinguish a freeway (motorway) from an
on/off-ramp (motorwayLink). A value of unknown means either the way's highway
tag was not one of the listed values or the loaded map tiles were generated
before this field existed and need to be re-downloaded.
* **distanceFromWayCenter**: Our distance from the center of the road based on
gps position data and the openstreetmap road path.
* **visionCurveSpeed**: The suggested speed based off of vision curve
calculations.
* **waySelectionType**: current, predicted, possible, extended, fail.
    * current indicates that we are still on the last osm way that we found.
    * predicted indicates that we attached to one of the upcoming osm ways from our predicted
path.
    * possible indicates that we picked a new road that was not based on
previously found values.
    * extended indicates that we stayed attached to the current way only because we could not find a better match and the current match isn't completely outside of gps position deviation.
    * fail indicates that we could not find any acceptable way to use as our current road.
* **speedLimitAccepted**: indicates if the current detected speed limit value is
  accepted.

## MapdExtendedOut
Contains additional data typically not needed during driving.

Output Frequency: 1hz
Queue Size: MEDIUM (2mb)

Suggested openpilot cereal settings:
Frequency: 1
Should Log: False
Decimation: -1

This message contains a lot of data that typically won't be needed during
debugging. As such I recommend not having it added to the logs so that we are
not unnecessarily using comma's storage for comma connect users.

### settings
The settings value in mapdExtendedOut is a json encoding of the currently active
settings. The json is the same format as the MapdSettings param.

### downloadProgress
* active: Indicates whether mapd is currently downloading maps
* cancelled: Indicates if the last download was cancelled
* totalFiles: How many files will be downloaded
* downloadedFiles: How many files have been downloaded
* locations: a list of locations that are being downloaded
* locationDetails: a list of download progress details for each location that is
  being downloaded
    * location: which location these details are for
    * totalFiles: how many files will be downloaded for the location
    * downloadedFiles: how many files have been downloaded for the location

### path
A list points of the current path mapd has attached to and their target
velocities and calculated curvatures.
* latitude: latitude of the position on the path.
* longitude: longitude of the position on the path.
* curvature: The curvature that was calculated for the point on the path
* targetVelocity: The velocity mapd has calculated will reach the target lateral
  acceleration at the point on the path.

### position
The current position mapd is using.
* latitude: latitude of the position.
* longitude: longitude of the position.

### loopRateAverage / loopRateMin
The average and minimum main loop update rate, in Hz, over the last 20 main
loop cycles. loopRateAverage is the mean rate across those cycles;
loopRateMin is the rate implied by the single slowest cycle in the window.

