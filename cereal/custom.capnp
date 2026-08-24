using Cxx = import "./include/c++.capnp";
$Cxx.namespace("cereal");

using Car = import "car.capnp";

@0xb526ba661d550a59;

# custom.capnp: a home for empty structs reserved for custom forks
# These structs are guaranteed to remain reserved and empty in mainline
# cereal, so use these if you want custom events in your fork.

# DO rename the structs
# DON'T change the identifier (e.g. @0x81c2f05a394cf4af)

struct StarPilotCarControl @0x81c2f05a394cf4af {
  hudControl @0 :HUDControl;

  struct HUDControl {
    audibleAlert @0 :AudibleAlert;

    enum AudibleAlert {
      none @0;

      engage @1;
      disengage @2;
      refuse @3;

      warningSoft @4;
      warningImmediate @5;

      prompt @6;
      promptRepeat @7;
      promptDistracted @8;

      # Random Events
      angry @9;
      continued @10;
      dejaVu @11;
      doc @12;
      fart @13;
      firefox @14;
      goat @15;
      hal9000 @16;
      mail @17;
      nessie @18;
      noice @19;
      startup @20;
      thisIsFine @21;
      uwu @22;
    }
  }
}

struct StarPilotCarParams @0xaedffd8f31e7b55d {
  alternativeExperience @0 :Int16;
  canUsePedal @1 :Bool;
  canUseSDSU @2 :Bool;
  flags @3 :UInt32;
  isHDA2 @4 :Bool;
  openpilotLongitudinalControlDisabled @5 :Bool;
  safetyConfigs @6 :List(SafetyConfig);
  pcmCruiseSpeed @7 :Bool = true;
  redneckCruiseAvailable @8 :Bool;

  struct SafetyConfig {
    safetyParam @0 :UInt16;
  }
}

struct StarPilotCarState @0xf35cc4560bbf6ec2 {
  accelPressed @0 :Bool;
  alwaysOnLateralEnabled @1 :Bool;
  brakeLights @2 :Bool;
  dashboardSpeedLimit @3 :Float32;
  decelPressed @4 :Bool;
  distancePressed @5 :Bool;
  distanceLongPressed @6 :Bool;
  distanceVeryLongPressed @7 :Bool;
  ecoGear @8 :Bool;
  forceCoast @9 :Bool;
  isParked @10 :Bool;
  pauseLateral @11 :Bool;
  pauseLongitudinal @12 :Bool;
  sportGear @13 :Bool;
  trafficModeEnabled @14 :Bool;
  gasStack @15 :Bool;  # Compatibility with older StarPilot payloads
  modePressed @16 :Bool;
  customPressed @17 :Bool;
  alwaysOnLateralAllowed @18 :Bool;
  dashboardStopSign @19 :UInt8;  # 0 = no signal / platform doesn't publish
  cancelPressed @20 :Bool;
  cancelLongPressed @21 :Bool;
  cancelVeryLongPressed @22 :Bool;
  pedalMaxRegen @23 :Bool;  # pedal at max regen, driver should use brake for more decel
  pedalLongActive @24 :Bool;  # Pre-AP pedal longitudinal mode is active (enableLongControl)
  teslaCCEngaged @25 :Bool;  # rising edge of stock Tesla CC engaging (no-pedal mode)
  teslaCCDisengaged @26 :Bool;  # falling edge of stock Tesla CC
  teslaCCNotArmed @27 :Bool;  # lateral engaged but DI_cruiseState != STANDBY/ENABLED
  accelHardCruise @28 :Bool;  # current/releasing accel cruise button came from GM hard-press signal
  decelHardCruise @29 :Bool;  # current/releasing decel cruise button came from GM hard-press signal
  pulseAndGlide @30 :Bool;  # developer-only wheel-button pulse-and-glide mode is enabled
}

struct StarPilotDeviceState @0xda96579883444c35 {
  freeSpace @0 :Int16;
  usedSpace @1 :Int16;
}

struct StarPilotModelDataV2 @0x80ae746ee2596b11 {
  turnDirection @0 :TurnDirection;

  enum TurnDirection {
    none @0;
    turnLeft @1;
    turnRight @2;
  }
}

struct StarPilotOnroadEvents @0xa5cd762cd951a455 {
  events @0 :List(StarPilotOnroadEvent);
}

struct StarPilotOnroadEvent @0xe344718567f9ce71 {
  name @0 :EventName;

  enable @1 :Bool;
  noEntry @2 :Bool;
  warning @3 :Bool;
  userDisable @4 :Bool;
  softDisable @5 :Bool;
  immediateDisable @6 :Bool;
  preEnable @7 :Bool;
  permanent @8 :Bool;
  overrideLateral @9 :Bool;
  overrideLongitudinal @10 :Bool;

  enum EventName {
    blockUser @0;
    customStartupAlert @1;
    forcingStop @2;
    goatSteerSaturated @3;
    greenLight @4;
    holidayActive @5;
    laneChangeBlockedLoud @6;
    leadDeparting @7;
    noLaneAvailable @8;
    nnffLoaded @9;
    openpilotCrashed @10;
    pedalInterceptorNoBrake @11;
    speedLimitChanged @12;
    trafficModeActive @13;
    trafficModeInactive @14;
    turningLeft @15;
    turningRight @16;

    # Random Events
    accel30 @17;
    accel35 @18;
    accel40 @19;
    dejaVuCurve @20;
    firefoxSteerSaturated @21;
    hal9000 @22;
    openpilotCrashedRandomEvent @23;
    thisIsFineSteerSaturated @24;
    toBeContinued @25;
    vCruise69 @26;
    yourFrogTriedToKillMe @27;
    youveGotMail @28;
    switchbackModeActive @29;
    switchbackModeInactive @30;
    lkasEnable @31;
    lkasDisable @32;
    lateralManeuver @33;
    pedalCruiseEnabled @34;
    pedalCruiseDisabled @35;
    pedalMaxRegen @36;
    teslaCCEngaged @37;
    teslaCCDisengaged @38;
    teslaCCNotArmed @39;
    pedalNotCalibrated @40;
  }
}

struct StarPilotPlan @0xf98d843bfd7004a3 {
  accelerationJerk @0 :Float32;
  cscControllingSpeed @1 :Bool;
  cscSpeed @2 :Float32;
  cscTraining @3 :Bool;
  dangerFactor @4 :Float32;
  dangerJerk @5 :Float32;
  desiredFollowDistance @6 :Int64;
  experimentalMode @7 :Bool;
  forcingStop @8 :Bool;
  forcingStopLength @9 :Float32;
  starpilotEvents @10 :List(StarPilotOnroadEvent);
  starpilotToggles @11 :Text;
  increasedStoppedDistance @12 :Float32;
  lateralCheck @13 :Bool;
  laneWidthLeft @14 :Float32;
  laneWidthRight @15 :Float32;
  maxAcceleration @16 :Float32;
  minAcceleration @17 :Float32;
  redLight @18 :Bool;
  roadCurvature @19 :Float32;
  slcMapSpeedLimit @20 :Float32;
  slcMapboxSpeedLimit @21 :Float32;
  slcNextSpeedLimit @22 :Float32;
  slcOverriddenSpeed @23 :Float32;
  slcSpeedLimit @24 :Float32;
  slcSpeedLimitOffset @25 :Float32;
  slcSpeedLimitSource @26 :Text;
  speedJerk @27 :Float32;
  speedLimitChanged @28 :Bool;
  tFollow @29 :Float32;
  themeUpdated @30 :Bool;
  unconfirmedSlcSpeedLimit @31 :Float32;
  vCruise @32 :Float32;
  weatherDaytime @33 :Bool;
  weatherId @34 :Int16;
  disableThrottle @35 :Bool;
  trackingLead @36 :Bool;
  stopSignConfirmed @37 :Bool;
  # Curve Speed Controller diagnostics, for tuning and rollout validation
  cscOverridden @38 :Bool;          # driver cancelled this curve with RES+
  cscLearnedLatAccel @39 :Float32;  # learned comfort at the current curvature, before margin
  cscBindingDistance @40 :Float32;  # distance to the horizon point setting the target, m
  approachStopLength @41 :Float32;  # pre-commit distance to a detected stop, m; 0 when off
}

struct StarPilotRadarState @0xb86e6369214c01c8 {
  leadLeft @0 :LeadData;
  leadRight @1 :LeadData;
  adjacentStopped @2 :AdjacentStopped;

  # A vehicle in an adjacent lane that was observed MOVING and then came to rest.
  # Distinct from leadLeft/leadRight, which are moving-target-only by design.
  struct AdjacentStopped {
    status @0 :Bool;
    dRel @1 :Float32;
    yRel @2 :Float32;
    radarTrackId @3 :Int32 = -1;
  }

  struct LeadData {
    dRel @0 :Float32;
    yRel @1 :Float32;
    vRel @2 :Float32;
    aRel @3 :Float32;
    vLead @4 :Float32;
    dPath @6 :Float32;
    vLat @7 :Float32;
    vLeadK @8 :Float32;
    aLeadK @9 :Float32;
    fcw @10 :Bool;
    status @11 :Bool;
    aLeadTau @12 :Float32;
    modelProb @13 :Float32;
    radar @14 :Bool;
    radarTrackId @15 :Int32 = -1;

    aLeadDEPRECATED @5 :Float32;
  }
}

struct StarPilotSelfdriveState @0xf416ec09499d9d19 {
  alertText1 @0 :Text;
  alertText2 @1 :Text;
  alertStatus @2 :AlertStatus;
  alertSize @3 :AlertSize;
  alertType @4 :Text;
  alertSound @5 :Car.CarControl.HUDControl.AudibleAlert;

  enum AlertStatus {
    normal @0;
    userPrompt @1;
    critical @2;
    starpilot @3;
  }

  enum AlertSize {
    none @0;
    small @1;
    mid @2;
    full @3;
  }
}

struct CustomReserved9 @0xa1680744031fdb2d {
  slotId @0 :Text;
  slotName @1 :Text;
  variant @2 :Text;
  variantLabel @3 :Text;
  reason @4 :Text;
  wallTimeNanos @5 :UInt64;
}

struct StarPilotLateralManeuverPlanDEPRECATED @0xcb9fd56c7057593a {
  desiredCurvature @0 :Float32;  # 1/m
}

struct StarPilotLateralState @0xc2243c65e0340384 {
  active @0 :Bool;
  frictionThreshold @1 :Float32;
  frictionScale @2 :Float32;
  feedforward @3 :Float32;
  frictionJerk @4 :Float32;
  frictionJerkDeadzone @5 :Float32;
  lowSpeedFactor @6 :Float32;
  unwindDetected @7 :Bool;
}

struct CustomReserved12 @0x9ccdc8676701b412 {
}

struct CustomReserved13 @0xcd96dafb67a082d0 {
}

struct CustomReserved14 @0xb057204d7deadf3f {
}

struct CustomReserved15 @0xbd443b539493bc68 {
}

struct CustomReserved16 @0xfc6241ed8877b611 {
}

struct MapdDownloadLocationDetails @0xff889853e7b0987f {
  location @0 :Text;
  totalFiles @1 :UInt32;
  downloadedFiles @2 :UInt32;
}

struct MapdDownloadProgress @0xfaa35dcac85073a2 {
  active @0 :Bool;
  cancelled @1 :Bool;
  totalFiles @2 :UInt32;
  downloadedFiles @3 :UInt32;
  locations @4 :List(Text);
  locationDetails @5 :List(MapdDownloadLocationDetails);
}

struct MapdPathPoint @0xd6f78acca1bc3939 {
  latitude @0 :Float64;
  longitude @1 :Float64;
  curvature @2 :Float32;
  targetVelocity @3 :Float32;
}

struct MapdExtendedOut @0xa30662f84033036c {
  downloadProgress @0 :MapdDownloadProgress;
  settings @1 :Text;
  path @2 :List(MapdPathPoint);
}

enum MapdInputType {
  download @0;
  setTargetLateralAccel @1;
  setSpeedLimitOffset @2;
  setSpeedLimitControl @3;
  setMapCurveSpeedControl @4;
  setVisionCurveSpeedControl @5;
  setLogLevel @6;
  setVisionCurveTargetLatA @7;
  setVisionCurveMinTargetV @8;
  reloadSettings @9;
  saveSettings @10;
  setEnableSpeed @11;
  setVisionCurveUseEnableSpeed @12;
  setMapCurveUseEnableSpeed @13;
  setSpeedLimitUseEnableSpeed @14;
  setHoldLastSeenSpeedLimit @15;
  setTargetSpeedJerk @16;
  setTargetSpeedAccel @17;
  setTargetSpeedTimeOffset @18;
  setDefaultLaneWidth @19;
  setMapCurveTargetLatA @20;
  loadDefaultSettings @21;
  loadRecommendedSettings @22;
  setSlowDownForNextSpeedLimit @23;
  setSpeedUpForNextSpeedLimit @24;
  setHoldSpeedLimitWhileChangingSetSpeed @25;
  loadPersistentSettings @26;
  cancelDownload @27;
  setLogJson @28;
  setLogSource @29;
  setExternalSpeedLimitControl @30;
  setExternalSpeedLimit @31;
  setSpeedLimitPriority @32;
  setSpeedLimitChangeRequiresAccept @33;
  acceptSpeedLimit @34;
  setPressGasToAcceptSpeedLimit @35;
  setAdjustSetSpeedToAcceptSpeedLimit @36;
  setAcceptSpeedLimitTimeout @37;
  setPressGasToOverrideSpeedLimit @38;
}

enum WaySelectionType {
  current @0;
  predicted @1;
  possible @2;
  extended @3;
  fail @4;
}

enum SpeedLimitOffsetType {
  static @0;
  percent @1;
}

struct MapdIn @0xc86a3d38d13eb3ef {
  type @0 :MapdInputType;
  float @1 :Float32;
  str @2 :Text;
  bool @3 :Bool;
}

enum RoadContext {
  freeway @0;
  city @1;
  unknown @2;
}

struct MapdOut @0xa4f1eb3323f5f582 {
  wayName @0 :Text;
  wayRef @1 :Text;
  roadName @2 :Text;
  speedLimit @3 :Float32;
  nextSpeedLimit @4 :Float32;
  nextSpeedLimitDistance @5 :Float32;
  hazard @6 :Text;
  nextHazard @7 :Text;
  nextHazardDistance @8 :Float32;
  advisorySpeed @9 :Float32;
  nextAdvisorySpeed @10 :Float32;
  nextAdvisorySpeedDistance @11 :Float32;
  oneWay @12 :Bool;
  lanes @13 :UInt8;
  tileLoaded @14 :Bool;
  speedLimitSuggestedSpeed @15 :Float32;
  suggestedSpeed @16 :Float32;
  estimatedRoadWidth @17 :Float32;
  roadContext @18 :RoadContext;
  distanceFromWayCenter @19 :Float32;
  visionCurveSpeed @20 :Float32;
  mapCurveSpeed @21 :Float32;
  waySelectionType @22 :WaySelectionType;
  speedLimitAccepted @23 :Bool;
}
