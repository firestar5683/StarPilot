#include "starpilot/ui/qt/offroad/longitudinal_settings.h"

StarPilotLongitudinalPanel::StarPilotLongitudinalPanel(StarPilotSettingsWindow *parent, bool forceOpen) : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  networkManager = new QNetworkAccessManager(this);

  QStackedLayout *longitudinalLayout = new QStackedLayout();
  addItem(longitudinalLayout);

  StarPilotListWidget *longitudinalList = new StarPilotListWidget(this);

  ScrollView *longitudinalPanel = new ScrollView(longitudinalList, this);

  longitudinalLayout->addWidget(longitudinalPanel);

  StarPilotListWidget *advancedLongitudinalTuneList = new StarPilotListWidget(this);
  StarPilotListWidget *aggressivePersonalityList = new StarPilotListWidget(this);
  StarPilotListWidget *conditionalExperimentalList = new StarPilotListWidget(this);
  StarPilotListWidget *curveSpeedList = new StarPilotListWidget(this);
  StarPilotListWidget *customDrivingPersonalityList = new StarPilotListWidget(this);
  StarPilotListWidget *longitudinalTuneList = new StarPilotListWidget(this);
  StarPilotListWidget *qolList = new StarPilotListWidget(this);
  StarPilotListWidget *relaxedPersonalityList = new StarPilotListWidget(this);
  StarPilotListWidget *speedLimitControllerList = new StarPilotListWidget(this);
  StarPilotListWidget *speedLimitControllerOffsetsList = new StarPilotListWidget(this);
  StarPilotListWidget *speedLimitControllerQOLList = new StarPilotListWidget(this);
  StarPilotListWidget *speedLimitControllerVisualList = new StarPilotListWidget(this);
  StarPilotListWidget *standardPersonalityList = new StarPilotListWidget(this);
  StarPilotListWidget *trafficPersonalityList = new StarPilotListWidget(this);
  StarPilotListWidget *weatherList = new StarPilotListWidget(this);
  StarPilotListWidget *weatherLowVisibilityList = new StarPilotListWidget(this);
  StarPilotListWidget *weatherRainList = new StarPilotListWidget(this);
  StarPilotListWidget *weatherRainStormList = new StarPilotListWidget(this);
  StarPilotListWidget *weatherSnowList = new StarPilotListWidget(this);

  ScrollView *advancedLongitudinalTunePanel = new ScrollView(advancedLongitudinalTuneList, this);
  ScrollView *aggressivePersonalityPanel = new ScrollView(aggressivePersonalityList, this);
  ScrollView *conditionalExperimentalPanel = new ScrollView(conditionalExperimentalList, this);
  ScrollView *curveSpeedPanel = new ScrollView(curveSpeedList, this);
  ScrollView *customDrivingPersonalityPanel = new ScrollView(customDrivingPersonalityList, this);
  ScrollView *longitudinalTunePanel = new ScrollView(longitudinalTuneList, this);
  ScrollView *qolPanel = new ScrollView(qolList, this);
  ScrollView *relaxedPersonalityPanel = new ScrollView(relaxedPersonalityList, this);
  ScrollView *speedLimitControllerPanel = new ScrollView(speedLimitControllerList, this);
  ScrollView *speedLimitControllerOffsetsPanel = new ScrollView(speedLimitControllerOffsetsList, this);
  ScrollView *speedLimitControllerQOLPanel = new ScrollView(speedLimitControllerQOLList, this);
  ScrollView *speedLimitControllerVisualPanel = new ScrollView(speedLimitControllerVisualList, this);
  ScrollView *standardPersonalityPanel = new ScrollView(standardPersonalityList, this);
  ScrollView *trafficPersonalityPanel = new ScrollView(trafficPersonalityList, this);
  ScrollView *weatherLowVisibilityPanel = new ScrollView(weatherLowVisibilityList, this);
  ScrollView *weatherPanel = new ScrollView(weatherList, this);
  ScrollView *weatherRainPanel = new ScrollView(weatherRainList, this);
  ScrollView *weatherRainStormPanel = new ScrollView(weatherRainStormList, this);
  ScrollView *weatherSnowPanel = new ScrollView(weatherSnowList, this);

  longitudinalLayout->addWidget(advancedLongitudinalTunePanel);
  longitudinalLayout->addWidget(aggressivePersonalityPanel);
  longitudinalLayout->addWidget(conditionalExperimentalPanel);
  longitudinalLayout->addWidget(curveSpeedPanel);
  longitudinalLayout->addWidget(customDrivingPersonalityPanel);
  longitudinalLayout->addWidget(longitudinalTunePanel);
  longitudinalLayout->addWidget(qolPanel);
  longitudinalLayout->addWidget(relaxedPersonalityPanel);
  longitudinalLayout->addWidget(speedLimitControllerPanel);
  longitudinalLayout->addWidget(speedLimitControllerOffsetsPanel);
  longitudinalLayout->addWidget(speedLimitControllerQOLPanel);
  longitudinalLayout->addWidget(speedLimitControllerVisualPanel);
  longitudinalLayout->addWidget(standardPersonalityPanel);
  longitudinalLayout->addWidget(trafficPersonalityPanel);
  longitudinalLayout->addWidget(weatherLowVisibilityPanel);
  longitudinalLayout->addWidget(weatherPanel);
  longitudinalLayout->addWidget(weatherRainPanel);
  longitudinalLayout->addWidget(weatherRainStormPanel);
  longitudinalLayout->addWidget(weatherSnowPanel);

  const std::vector<std::tuple<QString, QString, QString, QString>> longitudinalToggles {
    {"AdvancedLongitudinalTune", tr("Advanced Longitudinal Tuning"), tr("<b>Advanced acceleration and braking control changes</b> to fine-tune how openpilot drives."), "../../starpilot/assets/toggle_icons/icon_advanced_longitudinal_tune.png"},
    {"EVTuning", tr("EV Tuning"), tr("<b>Use acceleration profiles tuned for EVs.</b> Defaults to the vehicle's detected powertrain type but can be overridden if the automatic choice doesn't match."), ""},
    {"TruckTuning", tr("Truck Tuning"), tr("<b>Use aggressive acceleration profiles tuned for trucks.</b> Intended for heavy vehicles that need stronger throttle."), ""},
    {"LongitudinalActuatorDelay", parent->longitudinalActuatorDelay != 0 ? QString(tr("Actuator Delay (Default: %1)")).arg(QString::number(parent->longitudinalActuatorDelay, 'f', 2)) : tr("Actuator Delay"), tr("<b>The time between openpilot's throttle or brake command and the vehicle's response.</b> Increase if the vehicle feels slow to react; decrease if it feels too eager or overshoots."), ""},
    {"MaxDesiredAcceleration", tr("Maximum Acceleration"), tr("<b>Limit the strongest acceleration</b> openpilot can command."), ""},
    {"StartAccel", parent->startAccel != 0 ? QString(tr("Start Acceleration (Default: %1)")).arg(QString::number(parent->startAccel, 'f', 2)) : tr("Start Acceleration"), tr("<b>Extra acceleration applied when starting from a stop.</b> Increase for quicker takeoffs; decrease for smoother, gentler starts."), ""},
    {"VEgoStarting", parent->vEgoStarting != 0 ? QString(tr("Start Speed (Default: %1)")).arg(QString::number(parent->vEgoStarting, 'f', 2)) : tr("Start Speed"), tr("<b>The speed at which openpilot exits the stopped state.</b> Increase to reduce creeping; decrease to move sooner after stopping."), ""},
    {"StopAccel", parent->stopAccel != 0 ? QString(tr("Stop Acceleration (Default: %1)")).arg(QString::number(parent->stopAccel, 'f', 2)) : tr("Stop Acceleration"), tr("<b>Brake force applied to hold the vehicle at a standstill.</b> Increase to prevent rolling on hills; decrease for smoother, softer stops."), ""},
    {"StoppingDecelRate", parent->stoppingDecelRate != 0 ? QString(tr("Stopping Rate (Default: %1)")).arg(QString::number(parent->stoppingDecelRate, 'f', 2)) : tr("Stopping Rate"), tr("<b>How quickly braking ramps up when stopping.</b> Increase for shorter, firmer stops; decrease for smoother, longer stops."), ""},
    {"VEgoStopping", parent->vEgoStopping != 0 ? QString(tr("Stop Speed (Default: %1)")).arg(QString::number(parent->vEgoStopping, 'f', 2)) : tr("Stop Speed"), tr("<b>The speed at which openpilot considers the vehicle stopped.</b> Increase to brake earlier and stop smoothly; decrease to wait longer but risk overshooting."), ""},

    {"ConditionalExperimental", tr("Conditional Experimental Mode"), tr("<b>Automatically switch to \"Experimental Mode\" when set conditions are met.</b> Allows the model to handle challenging situations with smarter decision making."), "../../starpilot/assets/toggle_icons/icon_conditional.png"},
    {"PersistExperimentalState", tr("Persist Experimental State"), tr("<b>Keep your manual Conditional Experimental override through reboots</b> until you manually clear it."), ""},
    {"CESpeed", tr("Below"), tr("<b>Switch to \"Experimental Mode\" when driving below this speed without a lead</b> to help openpilot handle low-speed situations more smoothly."), ""},
    {"CECurves", tr("Curve Detected Ahead"), tr("<b>Switch to \"Experimental Mode\" when a curve is detected</b> to allow the model to set an appropriate speed for the curve."), ""},
    {"CEStopLights", tr("\"Detected\" Stop Lights/Signs"), tr("<b>Switch to \"Experimental Mode\" whenever the driving model \"detects\" a red light or stop sign.</b><br><br><i><b>Disclaimer</b>: openpilot does not explicitly detect traffic lights or stop signs. In \"Experimental Mode\", openpilot makes end-to-end driving decisions from camera input, which means it may stop even when there's no clear reason!</i>"), ""},
    {"CELead", tr("Lead Detected Ahead"), tr("<b>Switch to \"Experimental Mode\" when a slower or stopped vehicle is detected.</b> Can make braking smoother and more reliable on some vehicles."), ""},
    {"CEModelStopTime", tr("Predicted Stop In"), tr("<b>Switch to \"Experimental Mode\" when openpilot predicts a stop within the set time.</b> This is usually triggered when the model \"sees\" a red light or stop sign ahead.<br><br><i><b>Disclaimer</b>: openpilot does not explicitly detect traffic lights or stop signs. In \"Experimental Mode\", openpilot makes end-to-end driving decisions from camera input, which means it may stop even when there's no clear reason!</i>"), ""},
    {"CESignalSpeed", tr("Turn Signal Below"), tr("<b>Switch to \"Experimental Mode\" when using a turn signal below the set speed</b> to allow the model to choose an appropriate speed for smoother left and right turns."), ""},
    {"ShowCEMStatus", tr("Status Widget"), tr("<b>Show which condition triggered \"Experimental Mode\"</b> on the driving screen."), ""},

    {"CurveSpeedController", tr("Curve Speed Controller"), tr("<b>Automatically slow down for upcoming curves</b> using data learned from your driving style, adapting to curves as you would."), "../../starpilot/assets/toggle_icons/icon_speed_map.png"},
    {"CalibratedLateralAcceleration", tr("Calibrated Lateral Acceleration"), tr("<b>The learned lateral acceleration from collected driving data.</b> This sets how fast openpilot will take curves. Higher values allow faster cornering; lower values slow the vehicle for gentler turns."), ""},
    {"CalibrationProgress", tr("Calibration Progress"), tr("<b>How much curve data has been collected.</b> This is a progress meter; it is normal for the value to stay low and rarely reach 100%."), ""},
    {"ResetCurveData", tr("Reset Curve Data"), tr("<b>Reset collected user data for \"Curve Speed Controller\".</b>"), ""},
    {"ShowCSCStatus", tr("Status Widget"), tr("<b>Show the \"Curve Speed Controller\" target speed on the driving screen.</b>"), ""},

    {"CustomPersonalities", tr("Driving Personalities"), tr("<b>Customize the \"Driving Personalities\"</b> to better match your driving style."), "../../starpilot/assets/toggle_icons/icon_personality.png"},

    {"TrafficPersonalityProfile", tr("Traffic Mode"), tr("<b>Customize the \"Traffic Mode\" personality profile.</b> Designed for stop-and-go driving."), "../../starpilot/assets/stock_theme/distance_icons/traffic.png"},
    {"TrafficFollow", tr("Following Distance"), tr("<b>The minimum following distance to the lead vehicle in \"Traffic Mode\".</b> openpilot blends between this value and the \"Aggressive\" profile as speed increases. Increase for more space; decrease for tighter gaps."), ""},
    {"TrafficJerkAcceleration", tr("Acceleration Smoothness"), tr("<b>How smoothly openpilot accelerates in \"Traffic Mode\".</b> Increase for gentler starts; decrease for faster but more abrupt takeoffs."), ""},
    {"TrafficJerkDeceleration", tr("Braking Smoothness"), tr("<b>How smoothly openpilot brakes in \"Traffic Mode\".</b> Increase for gentler stops; decrease for quicker but sharper braking."), ""},
    {"TrafficJerkDanger", tr("Safety Gap Bias"), tr("<b>How much extra space openpilot keeps from the vehicle ahead in \"Traffic Mode\".</b> Increase for larger gaps and more cautious following; decrease for tighter gaps and closer following."), ""},
    {"TrafficJerkSpeedDecrease", tr("Slowdown Response"), tr("<b>How smoothly openpilot slows down in \"Traffic Mode\".</b> Increase for more gradual deceleration; decrease for faster but sharper slowdowns."), ""},
    {"TrafficJerkSpeed", tr("Speed-Up Response"), tr("<b>How smoothly openpilot speeds up in \"Traffic Mode\".</b> Increase for more gradual acceleration; decrease for quicker but more jolting acceleration."), ""},
    {"ResetTrafficPersonality", tr("Reset to Defaults"), tr("<b>Reset \"Traffic Mode\" settings to defaults.</b>"), ""},

    {"AggressivePersonalityProfile", tr("Aggressive"), tr("<b>Customize the \"Aggressive\" personality profile.</b> Designed for assertive driving with tighter gaps."), "../../starpilot/assets/stock_theme/distance_icons/aggressive.png"},
    {"AggressiveFollow", tr("Following Distance"), tr("<b>How many seconds openpilot follows behind lead vehicles when using the \"Aggressive\" profile.</b> Increase for more space; decrease for tighter gaps.<br><br>Default: 1.25 seconds."), ""},
    {"AggressiveFollowHigh", tr("High Speed Following Distance"), tr("<b>Following distance for higher speeds in the \"Aggressive\" profile.</b> openpilot smoothly blends from the base value to this value as speed rises."), ""},
    {"AggressiveJerkAcceleration", tr("Acceleration Smoothness"), tr("<b>How smoothly openpilot accelerates with the \"Aggressive\" profile.</b> Increase for gentler starts; decrease for faster but more abrupt takeoffs."), ""},
    {"AggressiveJerkDeceleration", tr("Braking Smoothness"), tr("<b>How smoothly openpilot brakes with the \"Aggressive\" profile.</b> Increase for gentler stops; decrease for quicker but sharper braking."), ""},
    {"AggressiveJerkDanger", tr("Safety Gap Bias"), tr("<b>How much extra space openpilot keeps from the vehicle ahead with the \"Aggressive\" profile.</b> Increase for larger gaps and more cautious following; decrease for tighter gaps and closer following."), ""},
    {"AggressiveJerkSpeedDecrease", tr("Slowdown Response"), tr("<b>How smoothly openpilot slows down with the \"Aggressive\" profile.</b> Increase for more gradual deceleration; decrease for faster but sharper slowdowns."), ""},
    {"AggressiveJerkSpeed", tr("Speed-Up Response"), tr("<b>How smoothly openpilot speeds up with the \"Aggressive\" profile.</b> Increase for more gradual acceleration; decrease for quicker but more jolting acceleration."), ""},
    {"ResetAggressivePersonality", tr("Reset to Defaults"), tr("<b>Reset the \"Aggressive\" profile to defaults.</b>"), ""},

    {"StandardPersonalityProfile", tr("Standard"), tr("<b>Customize the \"Standard\" personality profile.</b> Designed for balanced driving with moderate gaps."), "../../starpilot/assets/stock_theme/distance_icons/standard.png"},
    {"StandardFollow", tr("Following Distance"), tr("<b>How many seconds openpilot follows behind lead vehicles when using the \"Standard\" profile.</b> Increase for more space; decrease for tighter gaps.<br><br>Default: 1.45 seconds."), ""},
    {"StandardFollowHigh", tr("High Speed Following Distance"), tr("<b>Following distance for higher speeds in the \"Standard\" profile.</b> openpilot smoothly blends from the base value to this value as speed rises."), ""},
    {"StandardJerkAcceleration", tr("Acceleration Smoothness"), tr("<b>How smoothly openpilot accelerates with the \"Standard\" profile.</b> Increase for gentler starts; decrease for faster but more abrupt takeoffs."), ""},
    {"StandardJerkDeceleration", tr("Braking Smoothness"), tr("<b>How smoothly openpilot brakes with the \"Standard\" profile.</b> Increase for gentler stops; decrease for quicker but sharper braking."), ""},
    {"StandardJerkDanger", tr("Safety Gap Bias"), tr("<b>How much extra space openpilot keeps from the vehicle ahead with the \"Standard\" profile.</b> Increase for larger gaps and more cautious following; decrease for tighter gaps and closer following."), ""},
    {"StandardJerkSpeedDecrease", tr("Slowdown Response"), tr("<b>How smoothly openpilot slows down with the \"Standard\" profile.</b> Increase for more gradual deceleration; decrease for faster but sharper slowdowns."), ""},
    {"StandardJerkSpeed", tr("Speed-Up Response"), tr("<b>How smoothly openpilot speeds up with the \"Standard\" profile.</b> Increase for more gradual acceleration; decrease for quicker but more jolting acceleration."), ""},
    {"ResetStandardPersonality", tr("Reset to Defaults"), tr("<b>Reset the \"Standard\" profile to defaults.</b>"), ""},

    {"RelaxedPersonalityProfile", tr("Relaxed"), tr("<b>Customize the \"Relaxed\" personality profile.</b> Designed for smoother, more comfortable driving with larger gaps."), "../../starpilot/assets/stock_theme/distance_icons/relaxed.png"},
    {"RelaxedFollow", tr("Following Distance"), tr("<b>How many seconds openpilot follows behind lead vehicles when using the \"Relaxed\" profile.</b> Increase for more space; decrease for tighter gaps.<br><br>Default: 1.6 seconds."), ""},
    {"RelaxedFollowHigh", tr("High Speed Following Distance"), tr("<b>Following distance for higher speeds in the \"Relaxed\" profile.</b> openpilot smoothly blends from the base value to this value as speed rises."), ""},
    {"RelaxedJerkAcceleration", tr("Acceleration Smoothness"), tr("<b>How smoothly openpilot accelerates with the \"Relaxed\" profile.</b> Increase for gentler starts; decrease for faster but more abrupt takeoffs."), ""},
    {"RelaxedJerkDeceleration", tr("Braking Smoothness"), tr("<b>How smoothly openpilot brakes with the \"Relaxed\" profile.</b> Increase for gentler stops; decrease for quicker but sharper braking."), ""},
    {"RelaxedJerkDanger", tr("Safety Gap Bias"), tr("<b>How much extra space openpilot keeps from the vehicle ahead with the \"Relaxed\" profile.</b> Increase for larger gaps and more cautious following; decrease for tighter gaps and closer following."), ""},
    {"RelaxedJerkSpeedDecrease", tr("Slowdown Response"), tr("<b>How smoothly openpilot slows down with the \"Relaxed\" profile.</b> Increase for more gradual deceleration; decrease for faster but sharper slowdowns."), ""},
    {"RelaxedJerkSpeed", tr("Speed-Up Response"), tr("<b>How smoothly openpilot speeds up with the \"Relaxed\" profile.</b> Increase for more gradual acceleration; decrease for quicker but more jolting acceleration."), ""},
    {"ResetRelaxedPersonality", tr("Reset to Defaults"), tr("<b>Reset the \"Relaxed\" profile to defaults.</b>"), ""},

    {"LongitudinalTune", tr("Longitudinal Tuning"), tr("<b>Acceleration and braking control changes</b> to fine-tune how openpilot drives."), "../../starpilot/assets/toggle_icons/icon_longitudinal_tune.png"},
    {"AccelerationProfile", tr("Acceleration Profile"), tr("<b>How quickly openpilot speeds up.</b> \"Eco\" is gentle and efficient, \"Sport\" is firmer and more responsive, and \"Sport+\" accelerates at the maximum rate allowed."), ""},
    {"DecelerationProfile", tr("Deceleration Profile"), tr("<b>How firmly openpilot slows down.</b> \"Eco\" favors coasting, \"Sport\" applies stronger braking."), ""},
    {"HumanAcceleration", tr("Human-Like Acceleration"), tr("<b>Acceleration that mimics human behavior</b> by easing the throttle at low speeds and adding extra power when taking off from a stop."), ""},
    {"CoastUpToLeads", tr("Coast Up To Leads"), tr("<b>Keep the optional far-lead comfort logic enabled, including gentle coasting and matched-follow smoothing for distant leads.</b> Recommended to leave on unless your vehicle shows lead-follow stutter or springy gas/brake behavior."), ""},
    {"HumanLaneChanges", tr("Human-Like Lane Changes"), tr("<b>Lane-change behavior that mimics human drivers</b> by anticipating and tracking adjacent vehicles during lane changes."), ""},
    {"LeadDetectionThreshold", tr("Lead Detection Sensitivity"), tr("<b>How sensitive openpilot is to detecting vehicles.</b> Higher sensitivity allows quicker detection at longer distances but may react to non-vehicle objects; lower sensitivity is more conservative and reduces false detections."), ""},
    {"TacoTune", tr("\"Taco Bell Run\" Turn Speed Hack"), tr("<b>The turn-speed hack from comma's 2022 \"Taco Bell Run\".</b> Designed to slow down for left and right turns."), ""},
    {"NavLongitudinalAllowed", tr("Use Route Speed Control"), tr("<b>Allow an active navigation route to reduce cruise speed for upcoming turns, ramps, and roundabouts.</b>"), ""},

    {"QOLLongitudinal", tr("Quality of Life"), tr("<b>Miscellaneous acceleration and braking control changes</b> to fine-tune how openpilot drives."), "../../starpilot/assets/toggle_icons/icon_quality_of_life.png"},
    {"CustomCruise", tr("Cruise Interval"), tr("<b>How much the set speed increases or decreases</b> for each + or – cruise control button press."), ""},
    {"CustomCruiseLong", tr("Cruise Interval (Hold)"), tr("<b>How much the set speed increases or decreases while holding the + or – cruise control buttons.</b>"), ""},
    {"ForceStops", tr("Force Stop at \"Detected\" Stop Lights/Signs"), tr("<b>Force openpilot to stop whenever the driving model \"detects\" a red light or stop sign.</b><br><br><i><b>Disclaimer</b>: openpilot does not explicitly detect traffic lights or stop signs. In \"Experimental Mode\", openpilot makes end-to-end driving decisions from camera input, which means it may stop even when there's no clear reason!</i>"), ""},
    {"ForceStopDistanceOffset", tr("Force Stop Distance Offset"), tr("<b>Tune where Force Stops bring the car to rest.</b> Positive values let the car roll further before stopping (longer stop, closer to the line). Negative values stop the car sooner (more buffer before the line)."), ""},
    {"ForceStandstill", tr("Force Standstill State"), tr("<b>Keep openpilot in the standstill state until you press the gas pedal or the Resume/+ cruise button.</b><br><br>This applies to any engaged stop, not just red lights or stop signs."), ""},
    {"RadarTakeoffs", tr("Radar for Takeoffs"), tr("<b>Turns on/off using radar data to track leads at standstill</b>, making following/takeoffs more responsive once leads move."), ""},
    {"IncreasedStoppedDistance", tr("Increase Stopped Distance by:"), tr("<b>Add extra space when stopped behind vehicles.</b> Increase for more room; decrease for shorter gaps."), ""},
    {"MapGears", tr("Map Accel/Decel to Gears"), tr("<b>Map the Acceleration or Deceleration profiles to the vehicle's \"Eco\" and \"Sport\" gear modes.</b>"), ""},
    {"SetSpeedOffset", tr("Offset Set Speed by:"), tr("<b>Increase the set speed by the chosen offset.</b> For example, set +5 if you usually drive 5 over the limit."), ""},
    {"ReverseCruise", tr("Reverse Cruise Increase"), tr("<b>Reverse the cruise control button behavior</b> so a short press increases the set speed by 5 instead of 1."), ""},
    {"WeatherPresets", tr("Weather Condition Offsets"), tr("<b>Automatically adjust driving behavior based on real-time weather.</b> Helps maintain comfort and safety in low visibility, rain, or snow."), ""},

    {"LowVisibilityOffsets", tr("Low Visibility"), tr("<b>Driving adjustments for fog, haze, or other low-visibility conditions.</b>"), ""},
    {"IncreaseFollowingLowVisibility", tr("Increase Following Distance by:"), tr("<b>Add extra space behind lead vehicles in low visibility.</b> Increase for more space; decrease for tighter gaps."), ""},
    {"IncreasedStoppedDistanceLowVisibility", tr("Increase Stopped Distance by:"), tr("<b>Add extra buffer when stopped behind vehicles in low visibility.</b> Increase for more room; decrease for shorter gaps."), ""},
    {"ReduceAccelerationLowVisibility", tr("Reduce Acceleration by:"), tr("<b>Lower the maximum acceleration in low visibility.</b> Increase for softer takeoffs; decrease for quicker but less stable takeoffs."), ""},
    {"ReduceLateralAccelerationLowVisibility", tr("Reduce Speed in Curves by:"), tr("<b>Lower the desired speed while driving through curves in low visibility.</b> Increase for safer, gentler turns; decrease for more aggressive driving in curves."), ""},

    {"RainOffsets", tr("Rain"), tr("<b>Driving adjustments for rainy conditions.</b>"), ""},
    {"IncreaseFollowingRain", tr("Increase Following Distance by:"), tr("<b>Add extra space behind lead vehicles in rain.</b> Increase for more space; decrease for tighter gaps."), ""},
    {"IncreasedStoppedDistanceRain", tr("Increase Stopped Distance by:"), tr("<b>Add extra buffer when stopped behind vehicles in rain.</b> Increase for more room; decrease for shorter gaps."), ""},
    {"ReduceAccelerationRain", tr("Reduce Acceleration by:"), tr("<b>Lower the maximum acceleration in rain.</b> Increase for softer takeoffs; decrease for quicker but less stable takeoffs."), ""},
    {"ReduceLateralAccelerationRain", tr("Reduce Speed in Curves by:"), tr("<b>Lower the desired speed while driving through curves in rain.</b> Increase for safer, gentler turns; decrease for more aggressive driving in curves."), ""},

    {"RainStormOffsets", tr("Rainstorms"), tr("<b>Driving adjustments for rainstorms.</b>"), ""},
    {"IncreaseFollowingRainStorm", tr("Increase Following Distance by:"), tr("<b>Add extra space behind lead vehicles in a rainstorm.</b> Increase for more space; decrease for tighter gaps."), ""},
    {"IncreasedStoppedDistanceRainStorm", tr("Increase Stopped Distance by:"), tr("<b>Add extra buffer when stopped behind vehicles in a rainstorm.</b> Increase for more room; decrease for shorter gaps."), ""},
    {"ReduceAccelerationRainStorm", tr("Reduce Acceleration by:"), tr("<b>Lower the maximum acceleration in a rainstorm.</b> Increase for softer takeoffs; decrease for quicker but less stable takeoffs."), ""},
    {"ReduceLateralAccelerationRainStorm", tr("Reduce Speed in Curves by:"), tr("<b>Lower the desired speed while driving through curves in a rainstorm.</b> Increase for safer, gentler turns; decrease for more aggressive driving in curves."), ""},

    {"SnowOffsets", tr("Snow"), tr("<b>Driving adjustments for snowy conditions.</b>"), ""},
    {"IncreaseFollowingSnow", tr("Increase Following Distance by:"), tr("<b>Add extra space behind lead vehicles in snow.</b> Increase for more space; decrease for tighter gaps."), ""},
    {"IncreasedStoppedDistanceSnow", tr("Increase Stopped Distance by:"), tr("<b>Add extra buffer when stopped behind vehicles in snow.</b> Increase for more room; decrease for shorter gaps."), ""},
    {"ReduceAccelerationSnow", tr("Reduce Acceleration by:"), tr("<b>Lower the maximum acceleration in snow.</b> Increase for softer takeoffs; decrease for quicker but less stable takeoffs."), ""},
    {"ReduceLateralAccelerationSnow", tr("Reduce Speed in Curves by:"), tr("<b>Lower the desired speed while driving through curves in snow.</b> Increase for safer, gentler turns; decrease for more aggressive driving in curves."), ""},


    {"SpeedLimitController", tr("Speed Limit Controller"), tr("<b>Limit openpilot's maximum driving speed to the current speed limit</b> obtained from downloaded maps, Mapbox, the dashboard, or vision-detected signs."), "../../starpilot/assets/toggle_icons/icon_speed_limit.png"},
    {"SLCFallback", tr("Fallback Speed"), tr("<b>The speed used by \"Speed Limit Controller\" when no speed limit is found.</b><br><br>- <b>Set Speed</b>: Use the cruise set speed<br>- <b>Experimental Mode</b>: Estimate the limit using the driving model<br>- <b>Previous Limit</b>: Keep using the last confirmed limit"), ""},
    {"SLCOverride", tr("Override Speed"), tr("<b>The speed used by \"Speed Limit Controller\" after you manually drive faster than the posted limit.</b><br><br>- <b>Set with Gas Pedal</b>: Use the highest speed reached while pressing the gas<br>- <b>Max Set Speed</b>: Use the cruise set speed<br><br>Overrides clear when openpilot disengages."), ""},
    {"SLCQOL", tr("Quality of Life"), tr("<b>Miscellaneous \"Speed Limit Controller\" changes</b> to fine-tune how openpilot drives."), ""},
    {"SLCConfirmation", tr("Confirm New Speed Limits"), tr("<b>Ask before changing to a new speed limit.</b> To accept, tap the flashing on-screen widget or press the Cruise Increase button. To deny, press the Cruise Decrease button or ignore the prompt for 30 seconds."), ""},
    {"SLCLookaheadHigher", tr("Higher Limit Lookahead Time"), tr("<b>How far ahead openpilot anticipates upcoming higher speed limits</b> from downloaded map data."), ""},
    {"SLCLookaheadLower", tr("Lower Limit Lookahead Time"), tr("<b>How far ahead openpilot anticipates upcoming lower speed limits</b> from downloaded map data."), ""},
    {"SetSpeedLimit", tr("Match Speed Limit on Engage"), tr("<b>When openpilot is first enabled, automatically set the max speed to the current posted limit.</b>"), ""},
    {"SLCMapboxFiller", tr("Use Mapbox as Fallback"), tr("<b>Use Mapbox speed-limit data when no other source is available.</b>"), ""},
    {"VisionSpeedLimitDetection", tr("Vision Speed Limit Detection"), tr("<b>Use the road camera to detect speed limit signs</b> for SLC and speed limit filling."), ""},
    {"SLCPriority", tr("Speed Limit Source Priority"), tr("<b>The source order for speed limits</b> when more than one is available."), ""},
    {"SLCOffsets", tr("Speed Limit Offsets"), tr("<b>Add an offset to the posted speed limit</b> to better match your driving style."), ""},
    {"Offset1", tr("Speed Offset (0–24 mph)"), tr("<b>How much to offset posted speed-limits</b> between 0 and 24 mph."), ""},
    {"Offset2", tr("Speed Offset (25–34 mph)"), tr("<b>How much to offset posted speed-limits</b> between 25 and 34 mph."), ""},
    {"Offset3", tr("Speed Offset (35–44 mph)"), tr("<b>How much to offset posted speed-limits</b> between 35 and 44 mph."), ""},
    {"Offset4", tr("Speed Offset (45–54 mph)"), tr("<b>How much to offset posted speed-limits</b> between 45 and 54 mph."), ""},
    {"Offset5", tr("Speed Offset (55–64 mph)"), tr("<b>How much to offset posted speed-limits</b> between 55 and 64 mph."), ""},
    {"Offset6", tr("Speed Offset (65–74 mph)"), tr("<b>How much to offset posted speed-limits</b> between 65 and 74 mph."), ""},
    {"Offset7", tr("Speed Offset (75–99 mph)"), tr("<b>How much to offset posted speed-limits</b> between 75 and 99 mph."), ""},
    {"SLCVisuals", tr("Visual Settings"), tr("<b>Visual \"Speed Limit Controller\" changes</b> to fine-tune how the driving screen looks."), ""},
    {"ShowSLCOffset", tr("Show Speed Limit Offset"), tr("<b>Show the current offset from the posted limit</b> on the driving screen."), ""},
    {"SpeedLimitSources", tr("Show Speed Limit Sources"), tr("<b>Display the speed-limit sources and their current values</b> on the driving screen."), ""},
    {"SLCAbbreviatedSources", tr("Show Abbreviated Icon Sources"), tr("<b>Render the speed-limit sources as compact text labels</b> (e.g. \"Dash-45\", \"MapD-30\") without icons."), ""},
    {"SLCActiveSourcesOnly", tr("Only Show Sources With Speed Limits"), tr("<b>Hide source rows that have no current speed limit reading</b>. Works with both abbreviated and full display."), ""}
  };

  for (const auto &[param, title, desc, icon] : longitudinalToggles) {
    AbstractControl *longitudinalToggle;

    if (param == "AdvancedLongitudinalTune") {
      StarPilotManageControl *advancedLongitudinalTuneToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(advancedLongitudinalTuneToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, advancedLongitudinalTunePanel]() {
        longitudinalLayout->setCurrentWidget(advancedLongitudinalTunePanel);
      });
      longitudinalToggle = advancedLongitudinalTuneToggle;
    } else if (param == "LongitudinalActuatorDelay") {
      longitudinalActuatorDelayToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 1, tr(" seconds"), std::map<float, QString>(), 0.01);
      longitudinalToggle = longitudinalActuatorDelayToggle;
    } else if (param == "MaxDesiredAcceleration") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0.1, 4.0, tr(" m/s²"), std::map<float, QString>(), 0.1);
    } else if (param == "StartAccel") {
      startAccelToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 4, tr(" m/s²"), std::map<float, QString>(), 0.01, true);
      longitudinalToggle = startAccelToggle;
    } else if (param == "VEgoStarting") {
      vEgoStartingToggle = new StarPilotParamValueControl(param, title, desc, icon, 0.01, 1, tr(" m/s²"), std::map<float, QString>(), 0.01);
      longitudinalToggle = vEgoStartingToggle;
    } else if (param == "StopAccel") {
      stopAccelToggle = new StarPilotParamValueControl(param, title, desc, icon, -4, 0, tr(" m/s²"), std::map<float, QString>(), 0.01, true);
      longitudinalToggle = stopAccelToggle;
    } else if (param == "StoppingDecelRate") {
      stoppingDecelRateToggle = new StarPilotParamValueControl(param, title, desc, icon, 0.001, 1, tr(" m/s²"), std::map<float, QString>(), 0.001, true);
      longitudinalToggle = stoppingDecelRateToggle;
    } else if (param == "VEgoStopping") {
      vEgoStoppingToggle = new StarPilotParamValueControl(param, title, desc, icon, 0.01, 1, tr(" m/s²"), std::map<float, QString>(), 0.01);
      longitudinalToggle = vEgoStoppingToggle;

    } else if (param == "ConditionalExperimental") {
      StarPilotManageControl *conditionalExperimentalToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(conditionalExperimentalToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, conditionalExperimentalPanel]() {
        longitudinalLayout->setCurrentWidget(conditionalExperimentalPanel);
      });
      longitudinalToggle = conditionalExperimentalToggle;
    } else if (param == "CESpeed") {
      StarPilotParamValueControl *CESpeed = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, tr(" mph"), std::map<float, QString>(), 1, true, 175);
      StarPilotParamValueControl *CESpeedLead = new StarPilotParamValueControl("CESpeedLead", tr("With Lead"), tr("<b>Switch to \"Experimental Mode\" when driving below this speed with a lead</b> to help openpilot handle low-speed situations more smoothly."), icon, 0, 99, tr(" mph"), std::map<float, QString>(), 1, true, 175);
      StarPilotDualParamValueControl *conditionalSpeeds = new StarPilotDualParamValueControl(CESpeed, CESpeedLead);
      longitudinalToggle = reinterpret_cast<AbstractControl*>(conditionalSpeeds);
    } else if (param == "CECurves") {
      std::vector<QString> curveToggles{"CECurvesLead"};
      std::vector<QString> curveToggleNames{tr("With Lead")};
      longitudinalToggle = new StarPilotButtonToggleControl(param, title, desc, icon, curveToggles, curveToggleNames);
    } else if (param == "CELead") {
      std::vector<QString> leadToggles{"CESlowerLead", "CEStoppedLead"};
      std::vector<QString> leadToggleNames{tr("Slower Lead"), tr("Stopped Lead")};
      longitudinalToggle = new StarPilotButtonToggleControl(param, title, desc, icon, leadToggles, leadToggleNames);
    } else if (param == "CEModelStopTime") {
      std::map<float, QString> stopTimeLabels;
      for (int i = 0; i <= 10; ++i) {
        stopTimeLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" second") : QString::number(i) + tr(" seconds");
      }
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 9, QString(), stopTimeLabels);
    } else if (param == "CESignalSpeed") {
      std::vector<QString> ceSignalToggles{"CESignalLaneDetection"};
      std::vector<QString> ceSignalToggleNames{tr("Not For Detected Lanes")};
      longitudinalToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, 0, 99, tr(" mph"), std::map<float, QString>(), 1.0, true, ceSignalToggles, ceSignalToggleNames, true);

    } else if (param == "CurveSpeedController") {
      StarPilotManageControl *curveControlToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(curveControlToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, curveSpeedPanel]() {
        longitudinalLayout->setCurrentWidget(curveSpeedPanel);
      });
      longitudinalToggle = curveControlToggle;
    } else if (param == "CalibrationProgress") {
      calibrationProgressLabel = new LabelControl(title, QString::number(params.getFloat("CalibrationProgress"), 'f', 2) + "%", desc);
      longitudinalToggle = calibrationProgressLabel;
    } else if (param == "CalibratedLateralAcceleration") {
      calibratedLateralAccelerationLabel = new LabelControl(title, QString::number(params.getFloat("CalibratedLateralAcceleration"), 'f', 2) + tr(" m/s²"), desc);
      longitudinalToggle = calibratedLateralAccelerationLabel;
    } else if (param == "ResetCurveData") {
      ButtonControl *resetCurveDataButton = new ButtonControl(title, tr("RESET"), desc);
      QObject::connect(resetCurveDataButton, &ButtonControl::clicked, [this]() {
        if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely reset your curvature data?"), this)) {
          params.putFloat("CalibratedLateralAcceleration", 2.00);
          params.remove("CalibrationProgress");
          params.remove("CurvatureData");

          calibratedLateralAccelerationLabel->setText(QString::number(2.00, 'f', 2) + tr(" m/s²"));
          calibrationProgressLabel->setText(QString::number(0.00, 'f', 2) + "%");
        }
      });
      longitudinalToggle = resetCurveDataButton;

    } else if (param == "CustomPersonalities") {
      StarPilotManageControl *customPersonalitiesToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(customPersonalitiesToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, customDrivingPersonalityPanel]() {
        longitudinalLayout->setCurrentWidget(customDrivingPersonalityPanel);
      });
      longitudinalToggle = customPersonalitiesToggle;
    } else if (param == "ResetTrafficPersonality" || param == "ResetAggressivePersonality" || param == "ResetStandardPersonality" || param == "ResetRelaxedPersonality") {
      ButtonControl *resetButton = new ButtonControl(title, tr("RESET"), desc);
      longitudinalToggle = resetButton;
    } else if (param == "TrafficPersonalityProfile") {
      StarPilotButtonsControl *trafficPersonalityToggle = new StarPilotButtonsControl(title, desc, icon, {tr("MANAGE")});
      QObject::connect(trafficPersonalityToggle, &StarPilotButtonsControl::buttonClicked, [longitudinalLayout, trafficPersonalityPanel, this](int id) {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(trafficPersonalityPanel);

        customPersonalityOpen = true;
      });
      longitudinalToggle = trafficPersonalityToggle;
    } else if (param == "AggressivePersonalityProfile") {
      StarPilotButtonsControl *aggressivePersonalityToggle = new StarPilotButtonsControl(title, desc, icon, {tr("MANAGE")});
      QObject::connect(aggressivePersonalityToggle, &StarPilotButtonsControl::buttonClicked, [longitudinalLayout, aggressivePersonalityPanel, this](int id) {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(aggressivePersonalityPanel);

        customPersonalityOpen = true;
      });
      longitudinalToggle = aggressivePersonalityToggle;
    } else if (param == "StandardPersonalityProfile") {
      StarPilotButtonsControl *standardPersonalityToggle = new StarPilotButtonsControl(title, desc, icon, {tr("MANAGE")});
      QObject::connect(standardPersonalityToggle, &StarPilotButtonsControl::buttonClicked, [longitudinalLayout, standardPersonalityPanel, this](int id) {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(standardPersonalityPanel);

        customPersonalityOpen = true;
      });
      longitudinalToggle = standardPersonalityToggle;
    } else if (param == "RelaxedPersonalityProfile") {
      StarPilotButtonsControl *relaxedPersonalityToggle = new StarPilotButtonsControl(title, desc, icon, {tr("MANAGE")});
      QObject::connect(relaxedPersonalityToggle, &StarPilotButtonsControl::buttonClicked, [longitudinalLayout, relaxedPersonalityPanel, this](int id) {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(relaxedPersonalityPanel);

        customPersonalityOpen = true;
      });
      longitudinalToggle = relaxedPersonalityToggle;
    } else if (aggressivePersonalityKeys.contains(param) || standardPersonalityKeys.contains(param) || relaxedPersonalityKeys.contains(param) || trafficPersonalityKeys.contains(param)) {
      if (param == "TrafficFollow" || param == "AggressiveFollow" || param == "AggressiveFollowHigh" ||
          param == "StandardFollow" || param == "StandardFollowHigh" || param == "RelaxedFollow" || param == "RelaxedFollowHigh") {
        std::map<float, QString> followTimeLabels;
        for (float i = 0; i <= 3; i += 0.01) {
          followTimeLabels[i] = std::lround(i / 0.01) == 1 / 0.01 ? QString::number(i, 'f', 2) + tr(" second") : QString::number(i, 'f', 2) + tr(" seconds");
        }
        if (param == "TrafficFollow") {
          longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0.5, 3, QString(), followTimeLabels, 0.01, true);
        } else {
          longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 1, 3, QString(), followTimeLabels, 0.01, true);
        }
      } else {
        longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 25, 200, "%");
      }

    } else if (param == "LongitudinalTune") {
      StarPilotManageControl *longitudinalTuneToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(longitudinalTuneToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, longitudinalTunePanel]() {
        longitudinalLayout->setCurrentWidget(longitudinalTunePanel);
      });
      longitudinalToggle = longitudinalTuneToggle;
    } else if (param == "AccelerationProfile") {
      std::vector<QString> accelerationProfiles{tr("Standard"), tr("Eco"), tr("Sport"), tr("Sport+")};
      ButtonParamControl *accelerationProfileToggle = new ButtonParamControl(param, title, desc, icon, accelerationProfiles);
      longitudinalToggle = accelerationProfileToggle;
    } else if (param == "DecelerationProfile") {
      std::vector<QString> decelerationProfiles{tr("Standard"), tr("Eco"), tr("Sport")};
      ButtonParamControl *decelerationProfileToggle = new ButtonParamControl(param, title, desc, icon, decelerationProfiles);
      longitudinalToggle = decelerationProfileToggle;
    } else if (param == "LeadDetectionThreshold") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 25, 50, "%");

    } else if (param == "QOLLongitudinal") {
      StarPilotManageControl *qolLongitudinalToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(qolLongitudinalToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, qolPanel]() {
        longitudinalLayout->setCurrentWidget(qolPanel);
      });
      longitudinalToggle = qolLongitudinalToggle;
    } else if (param == "CustomCruise") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 1, 99, tr(" mph"));
    } else if (param == "CustomCruiseLong") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 1, 99, tr(" mph"));
    } else if (param == "IncreasedStoppedDistance") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 10, tr(" feet"));
    } else if (param == "ForceStopDistanceOffset") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, -20, 20, tr(" feet"));
    } else if (param == "MapGears") {
      std::vector<QString> mapGearsToggles{"MapAcceleration", "MapDeceleration"};
      std::vector<QString> mapGearsToggleNames{tr("Acceleration"), tr("Deceleration")};
      longitudinalToggle = new StarPilotButtonToggleControl(param, title, desc, icon, mapGearsToggles, mapGearsToggleNames);
    } else if (param == "SetSpeedOffset") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, tr(" mph"));
    } else if (param == "WeatherPresets") {
      StarPilotManageControl *weatherToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(weatherToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, weatherPanel, this]() {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(weatherPanel);

        qolOpen = true;
      });
      longitudinalToggle = weatherToggle;
    } else if (param == "LowVisibilityOffsets") {
      ButtonControl *manageLowVisibilitOffsetsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageLowVisibilitOffsetsButton, &ButtonControl::clicked, [longitudinalLayout, weatherLowVisibilityPanel, this]() {
        openSubSubSubPanel();

        longitudinalLayout->setCurrentWidget(weatherLowVisibilityPanel);

        weatherOpen = true;
      });
      longitudinalToggle = manageLowVisibilitOffsetsButton;
    } else if (param == "RainOffsets") {
      ButtonControl *manageRainOffsetsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageRainOffsetsButton, &ButtonControl::clicked, [longitudinalLayout, weatherRainPanel, this]() {
        openSubSubSubPanel();

        longitudinalLayout->setCurrentWidget(weatherRainPanel);

        weatherOpen = true;
      });
      longitudinalToggle = manageRainOffsetsButton;
    } else if (param == "RainStormOffsets") {
      ButtonControl *manageRainStormOffsetsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageRainStormOffsetsButton, &ButtonControl::clicked, [longitudinalLayout, weatherRainStormPanel, this]() {
        openSubSubSubPanel();

        longitudinalLayout->setCurrentWidget(weatherRainStormPanel);

        weatherOpen = true;
      });
      longitudinalToggle = manageRainStormOffsetsButton;
    } else if (param == "SnowOffsets") {
      ButtonControl *manageSnowOffsetsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageSnowOffsetsButton, &ButtonControl::clicked, [longitudinalLayout, weatherSnowPanel, this]() {
        openSubSubSubPanel();

        longitudinalLayout->setCurrentWidget(weatherSnowPanel);

        weatherOpen = true;
      });
      longitudinalToggle = manageSnowOffsetsButton;
    } else if (param == "IncreaseFollowingLowVisibility" || param == "IncreaseFollowingRain" || param == "IncreaseFollowingRainStorm" || param == "IncreaseFollowingSnow") {
      std::map<float, QString> followTimeLabels;
      for (float i = 0; i <= 3; i += 0.01) {
        followTimeLabels[i] = std::lround(i / 0.01) == 1 / 0.01 ? QString::number(i, 'f', 2) + tr(" second") : QString::number(i, 'f', 2) + tr(" seconds");
      }
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 3, QString(), followTimeLabels, 0.01, true);
    } else if (param == "IncreasedStoppedDistanceLowVisibility" || param == "IncreasedStoppedDistanceRain" || param == "IncreasedStoppedDistanceRainStorm" || param == "IncreasedStoppedDistanceSnow") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 10, tr(" feet"));
    } else if (param == "ReduceAccelerationLowVisibility" || param == "ReduceAccelerationRain" || param == "ReduceAccelerationRainStorm" || param == "ReduceAccelerationSnow") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, "%", std::map<float, QString>(), 1);
    } else if (param == "ReduceLateralAccelerationLowVisibility" || param == "ReduceLateralAccelerationRain" || param == "ReduceLateralAccelerationRainStorm" || param == "ReduceLateralAccelerationSnow") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, "%", std::map<float, QString>(), 1);

    } else if (param == "SpeedLimitController") {
      StarPilotManageControl *speedLimitControllerToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(speedLimitControllerToggle, &StarPilotManageControl::manageButtonClicked, [longitudinalLayout, speedLimitControllerPanel]() {
        longitudinalLayout->setCurrentWidget(speedLimitControllerPanel);
      });
      longitudinalToggle = speedLimitControllerToggle;
    } else if (param == "SLCFallback") {
      std::vector<QString> fallbackOptions{tr("Set Speed"), tr("Experimental Mode"), tr("Previous Limit")};
      ButtonParamControl *fallbackSelection = new ButtonParamControl(param, title, desc, icon, fallbackOptions);
      longitudinalToggle = fallbackSelection;
    } else if (param == "SLCOverride") {
      std::vector<QString> overrideOptions{tr("None"), tr("Set With Gas Pedal"), tr("Max Set Speed")};
      ButtonParamControl *overrideSelection = new ButtonParamControl(param, title, desc, icon, overrideOptions);
      longitudinalToggle = overrideSelection;
    } else if (param == "SLCPriority") {
      ButtonControl *slcPriorityButton = new ButtonControl(title, tr("SELECT"), desc);
      QStringList primaryPriorities = {tr("Dashboard"), tr("Map Data"), tr("Vision"), tr("Highest"), tr("Lowest")};
      QStringList otherPriorities = {tr("None"), tr("Dashboard"), tr("Map Data"), tr("Vision")};
      QStringList priorityPrompts = {tr("Select your primary priority"), tr("Select your secondary priority")};

      QObject::connect(slcPriorityButton, &ButtonControl::clicked, [=]() {
        QStringList selectedPriorities;

        for (int i = 1; i <= 2; ++i) {
          QStringList availablePriorities = i == 1 ? primaryPriorities : otherPriorities;
          availablePriorities = availablePriorities.toSet().subtract(selectedPriorities.toSet()).toList();

          if (!parent->hasDashSpeedLimits) {
            availablePriorities.removeAll(tr("Dashboard"));
          }
          if (availablePriorities.size() == 1 && availablePriorities.contains(tr("None"))) {
            break;
          }

          QString selection = MultiOptionDialog::getSelection(priorityPrompts[i - 1], availablePriorities, "", this);
          if (selection.isEmpty()) {
            if (i == 2 && !selectedPriorities.isEmpty()) {
              params.put("SLCPriority2", tr("None").toStdString());
            }
            break;
          }

          selectedPriorities.append(selection);

          params.put(QString("SLCPriority%1").arg(i).toStdString(), selection.toStdString());
          if (selection == tr("None") || selection == tr("Lowest") || selection == tr("Highest")) {
            for (int j = i + 1; j <= 2; ++j) {
              params.put(QString("SLCPriority%1").arg(j).toStdString(), tr("None").toStdString());
            }
            break;
          }
        }

        selectedPriorities.removeAll(tr("None"));
        if (!selectedPriorities.isEmpty()) {
          slcPriorityButton->setValue(selectedPriorities.join(", "));
        }
      });

      QStringList selectedPriorities;
      for (int i = 1; i <= 2; ++i) {
        QString priority = QString::fromStdString(params.get(QString("SLCPriority%1").arg(i).toStdString()));
        if (primaryPriorities.contains(priority)) {
          selectedPriorities.append(priority);
        }
      }
      slcPriorityButton->setValue(selectedPriorities.join(", "));

      longitudinalToggle = slcPriorityButton;
    } else if (param == "SLCOffsets") {
      ButtonControl *manageSLCOffsetsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageSLCOffsetsButton, &ButtonControl::clicked, [longitudinalLayout, speedLimitControllerOffsetsPanel, this]() {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(speedLimitControllerOffsetsPanel);

        slcOpen = true;
      });
      longitudinalToggle = manageSLCOffsetsButton;
    } else if (speedLimitControllerOffsetsKeys.contains(param)) {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, -99, 99, tr(" mph"));
    } else if (param == "SLCQOL") {
      ButtonControl *manageSLCQOLButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageSLCQOLButton, &ButtonControl::clicked, [longitudinalLayout, speedLimitControllerQOLPanel, this]() {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(speedLimitControllerQOLPanel);

        slcOpen = true;
      });
      longitudinalToggle = manageSLCQOLButton;
    } else if (param == "SLCConfirmation") {
      std::vector<QString> confirmationToggles{"SLCConfirmationLower", "SLCConfirmationHigher"};
      std::vector<QString> confirmationToggleNames{tr("Lower Limits"), tr("Higher Limits")};
      longitudinalToggle = new StarPilotButtonToggleControl(param, title, desc, icon, confirmationToggles, confirmationToggleNames);
    } else if (param == "SLCLookaheadHigher" || param == "SLCLookaheadLower") {
      longitudinalToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 30, tr(" seconds"));
    } else if (param == "SLCVisuals") {
      ButtonControl *manageSLCVisualsButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(manageSLCVisualsButton, &ButtonControl::clicked, [longitudinalLayout, speedLimitControllerVisualPanel, this]() {
        openSubSubPanel();

        longitudinalLayout->setCurrentWidget(speedLimitControllerVisualPanel);

        slcOpen = true;
      });
      longitudinalToggle = manageSLCVisualsButton;

    } else {
      longitudinalToggle = new ParamControl(param, title, desc, icon);
    }

    toggles[param] = longitudinalToggle;

    if (advancedLongitudinalTuneKeys.contains(param)) {
      advancedLongitudinalTuneList->addItem(longitudinalToggle);
    } else if (aggressivePersonalityKeys.contains(param)) {
      aggressivePersonalityList->addItem(longitudinalToggle);
    } else if (conditionalExperimentalKeys.contains(param)) {
      conditionalExperimentalList->addItem(longitudinalToggle);
    } else if (curveSpeedKeys.contains(param)) {
      curveSpeedList->addItem(longitudinalToggle);
    } else if (customDrivingPersonalityKeys.contains(param)) {
      customDrivingPersonalityList->addItem(longitudinalToggle);
    } else if (longitudinalTuneKeys.contains(param)) {
      longitudinalTuneList->addItem(longitudinalToggle);
    } else if (qolKeys.contains(param)) {
      qolList->addItem(longitudinalToggle);
    } else if (relaxedPersonalityKeys.contains(param)) {
      relaxedPersonalityList->addItem(longitudinalToggle);
    } else if (speedLimitControllerKeys.contains(param)) {
      speedLimitControllerList->addItem(longitudinalToggle);
    } else if (speedLimitControllerOffsetsKeys.contains(param)) {
      speedLimitControllerOffsetsList->addItem(longitudinalToggle);
    } else if (speedLimitControllerQOLKeys.contains(param)) {
      speedLimitControllerQOLList->addItem(longitudinalToggle);
    } else if (speedLimitControllerVisualKeys.contains(param)) {
      speedLimitControllerVisualList->addItem(longitudinalToggle);
    } else if (standardPersonalityKeys.contains(param)) {
      standardPersonalityList->addItem(longitudinalToggle);
    } else if (trafficPersonalityKeys.contains(param)) {
      trafficPersonalityList->addItem(longitudinalToggle);
    } else if (weatherKeys.contains(param)) {
      weatherList->addItem(longitudinalToggle);
    } else if (weatherLowVisibilityKeys.contains(param)) {
      weatherLowVisibilityList->addItem(longitudinalToggle);
    } else if (weatherRainKeys.contains(param)) {
      weatherRainList->addItem(longitudinalToggle);
    } else if (weatherRainStormKeys.contains(param)) {
      weatherRainStormList->addItem(longitudinalToggle);
    } else if (weatherSnowKeys.contains(param)) {
      weatherSnowList->addItem(longitudinalToggle);
    } else {
      longitudinalList->addItem(longitudinalToggle);

      parentKeys.insert(param);
    }

    if (StarPilotManageControl *frogPilotManageToggle = qobject_cast<StarPilotManageControl*>(longitudinalToggle)) {
      QObject::connect(frogPilotManageToggle, &StarPilotManageControl::manageButtonClicked, [this]() {
        emit openSubPanel();
        openDescriptions(forceOpenDescriptions, toggles);
      });
    }

    QObject::connect(longitudinalToggle, &AbstractControl::hideDescriptionEvent, [this]() {
      update();
    });
    QObject::connect(longitudinalToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  QSet<QString> forceUpdateKeys = {"HumanAcceleration", "LongitudinalTune"};
  for (const QString &key : forceUpdateKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, this, &StarPilotLongitudinalPanel::updateToggles);
  }

  QObject::connect(static_cast<ToggleControl*>(toggles["EVTuning"]), &ToggleControl::toggleFlipped, this, [this]() {
    if (params.getBool("EVTuning")) {
      params.putBool("TruckTuning", false);
    }
    updateToggles();
  });
  QObject::connect(static_cast<ToggleControl*>(toggles["TruckTuning"]), &ToggleControl::toggleFlipped, this, [this]() {
    if (params.getBool("TruckTuning")) {
      params.putBool("EVTuning", false);
    }
    updateToggles();
  });

  StarPilotParamValueControl *trafficFollowToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficFollow"]);
  StarPilotParamValueControl *trafficAccelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficJerkAcceleration"]);
  StarPilotParamValueControl *trafficDecelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficJerkDeceleration"]);
  StarPilotParamValueControl *trafficDangerToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficJerkDanger"]);
  StarPilotParamValueControl *trafficSpeedToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficJerkSpeed"]);
  StarPilotParamValueControl *trafficSpeedDecreaseToggle = static_cast<StarPilotParamValueControl*>(toggles["TrafficJerkSpeedDecrease"]);
  StarPilotButtonsControl *trafficResetButton = static_cast<StarPilotButtonsControl*>(toggles["ResetTrafficPersonality"]);
  QObject::connect(trafficResetButton, &StarPilotButtonsControl::buttonClicked, [=]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely reset your settings for <b>Traffic Mode</b>?"), this)) {
      params.putFloat("TrafficFollow", std::stof(params.getKeyDefaultValue("TrafficFollow").value()));
      params.putFloat("TrafficJerkAcceleration", std::stof(params.getKeyDefaultValue("TrafficJerkAcceleration").value()));
      params.putFloat("TrafficJerkDeceleration", std::stof(params.getKeyDefaultValue("TrafficJerkDeceleration").value()));
      params.putFloat("TrafficJerkDanger", std::stof(params.getKeyDefaultValue("TrafficJerkDanger").value()));
      params.putFloat("TrafficJerkSpeed", std::stof(params.getKeyDefaultValue("TrafficJerkSpeed").value()));
      params.putFloat("TrafficJerkSpeedDecrease", std::stof(params.getKeyDefaultValue("TrafficJerkSpeedDecrease").value()));

      trafficFollowToggle->refresh();
      trafficAccelerationToggle->refresh();
      trafficDecelerationToggle->refresh();
      trafficDangerToggle->refresh();
      trafficSpeedToggle->refresh();
      trafficSpeedDecreaseToggle->refresh();
    }
  });

  StarPilotParamValueControl *aggressiveFollowToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveFollow"]);
  StarPilotParamValueControl *aggressiveFollowHighToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveFollowHigh"]);
  StarPilotParamValueControl *aggressiveAccelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveJerkAcceleration"]);
  StarPilotParamValueControl *aggressiveDecelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveJerkDeceleration"]);
  StarPilotParamValueControl *aggressiveDangerToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveJerkDanger"]);
  StarPilotParamValueControl *aggressiveSpeedToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveJerkSpeed"]);
  StarPilotParamValueControl *aggressiveSpeedDecreaseToggle = static_cast<StarPilotParamValueControl*>(toggles["AggressiveJerkSpeedDecrease"]);
  StarPilotButtonsControl *aggressiveResetButton = static_cast<StarPilotButtonsControl*>(toggles["ResetAggressivePersonality"]);
  QObject::connect(aggressiveResetButton, &StarPilotButtonsControl::buttonClicked, [=]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely reset your settings for the <b>Aggressive</b> personality?"), this)) {
      params.putFloat("AggressiveFollow", std::stof(params.getKeyDefaultValue("AggressiveFollow").value()));
      params.putFloat("AggressiveFollowHigh", std::stof(params.getKeyDefaultValue("AggressiveFollowHigh").value()));
      params.putFloat("AggressiveJerkAcceleration", std::stof(params.getKeyDefaultValue("AggressiveJerkAcceleration").value()));
      params.putFloat("AggressiveJerkDeceleration", std::stof(params.getKeyDefaultValue("AggressiveJerkDeceleration").value()));
      params.putFloat("AggressiveJerkDanger", std::stof(params.getKeyDefaultValue("AggressiveJerkDanger").value()));
      params.putFloat("AggressiveJerkSpeed", std::stof(params.getKeyDefaultValue("AggressiveJerkSpeed").value()));
      params.putFloat("AggressiveJerkSpeedDecrease", std::stof(params.getKeyDefaultValue("AggressiveJerkSpeedDecrease").value()));

      aggressiveFollowToggle->refresh();
      aggressiveFollowHighToggle->refresh();
      aggressiveAccelerationToggle->refresh();
      aggressiveDecelerationToggle->refresh();
      aggressiveDangerToggle->refresh();
      aggressiveSpeedToggle->refresh();
      aggressiveSpeedDecreaseToggle->refresh();
    }
  });

  StarPilotParamValueControl *standardFollowToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardFollow"]);
  StarPilotParamValueControl *standardFollowHighToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardFollowHigh"]);
  StarPilotParamValueControl *standardAccelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardJerkAcceleration"]);
  StarPilotParamValueControl *standardDecelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardJerkDeceleration"]);
  StarPilotParamValueControl *standardDangerToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardJerkDanger"]);
  StarPilotParamValueControl *standardSpeedToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardJerkSpeed"]);
  StarPilotParamValueControl *standardSpeedDecreaseToggle = static_cast<StarPilotParamValueControl*>(toggles["StandardJerkSpeedDecrease"]);
  StarPilotButtonsControl *standardResetButton = static_cast<StarPilotButtonsControl*>(toggles["ResetStandardPersonality"]);
  QObject::connect(standardResetButton, &StarPilotButtonsControl::buttonClicked, [=]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely reset your settings for the <b>Standard</b> personality?"), this)) {
      params.putFloat("StandardFollow", std::stof(params.getKeyDefaultValue("StandardFollow").value()));
      params.putFloat("StandardFollowHigh", std::stof(params.getKeyDefaultValue("StandardFollowHigh").value()));
      params.putFloat("StandardJerkAcceleration", std::stof(params.getKeyDefaultValue("StandardJerkAcceleration").value()));
      params.putFloat("StandardJerkDeceleration", std::stof(params.getKeyDefaultValue("StandardJerkDeceleration").value()));
      params.putFloat("StandardJerkDanger", std::stof(params.getKeyDefaultValue("StandardJerkDanger").value()));
      params.putFloat("StandardJerkSpeed", std::stof(params.getKeyDefaultValue("StandardJerkSpeed").value()));
      params.putFloat("StandardJerkSpeedDecrease", std::stof(params.getKeyDefaultValue("StandardJerkSpeedDecrease").value()));

      standardFollowToggle->refresh();
      standardFollowHighToggle->refresh();
      standardAccelerationToggle->refresh();
      standardDecelerationToggle->refresh();
      standardDangerToggle->refresh();
      standardSpeedToggle->refresh();
      standardSpeedDecreaseToggle->refresh();
    }
  });

  StarPilotParamValueControl *relaxedFollowToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedFollow"]);
  StarPilotParamValueControl *relaxedFollowHighToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedFollowHigh"]);
  StarPilotParamValueControl *relaxedAccelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedJerkAcceleration"]);
  StarPilotParamValueControl *relaxedDecelerationToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedJerkDeceleration"]);
  StarPilotParamValueControl *relaxedDangerToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedJerkDanger"]);
  StarPilotParamValueControl *relaxedSpeedToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedJerkSpeed"]);
  StarPilotParamValueControl *relaxedSpeedDecreaseToggle = static_cast<StarPilotParamValueControl*>(toggles["RelaxedJerkSpeedDecrease"]);
  StarPilotButtonsControl *relaxedResetButton = static_cast<StarPilotButtonsControl*>(toggles["ResetRelaxedPersonality"]);
  QObject::connect(relaxedResetButton, &StarPilotButtonsControl::buttonClicked, [=]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely reset your settings for the <b>Relaxed</b> personality?"), this)) {
      params.putFloat("RelaxedFollow", std::stof(params.getKeyDefaultValue("RelaxedFollow").value()));
      params.putFloat("RelaxedFollowHigh", std::stof(params.getKeyDefaultValue("RelaxedFollowHigh").value()));
      params.putFloat("RelaxedJerkAcceleration", std::stof(params.getKeyDefaultValue("RelaxedJerkAcceleration").value()));
      params.putFloat("RelaxedJerkDeceleration", std::stof(params.getKeyDefaultValue("RelaxedJerkDeceleration").value()));
      params.putFloat("RelaxedJerkDanger", std::stof(params.getKeyDefaultValue("RelaxedJerkDanger").value()));
      params.putFloat("RelaxedJerkSpeed", std::stof(params.getKeyDefaultValue("RelaxedJerkSpeed").value()));
      params.putFloat("RelaxedJerkSpeedDecrease", std::stof(params.getKeyDefaultValue("RelaxedJerkSpeedDecrease").value()));

      relaxedFollowToggle->refresh();
      relaxedFollowHighToggle->refresh();
      relaxedAccelerationToggle->refresh();
      relaxedDecelerationToggle->refresh();
      relaxedDangerToggle->refresh();
      relaxedSpeedToggle->refresh();
      relaxedSpeedDecreaseToggle->refresh();
    }
  });

  openDescriptions(forceOpenDescriptions, toggles);

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [longitudinalLayout, longitudinalPanel, this] {
    openDescriptions(forceOpenDescriptions, toggles);
    longitudinalLayout->setCurrentWidget(longitudinalPanel);
  });
  QObject::connect(parent, &StarPilotSettingsWindow::closeSubSubPanel, [longitudinalLayout, customDrivingPersonalityPanel, qolPanel, speedLimitControllerPanel, this]() {
    openDescriptions(forceOpenDescriptions, toggles);

    if (customPersonalityOpen) {
      longitudinalLayout->setCurrentWidget(customDrivingPersonalityPanel);

      customPersonalityOpen = false;
    } else if (qolOpen) {
      longitudinalLayout->setCurrentWidget(qolPanel);

      qolOpen = false;
    } else if (slcOpen) {
      longitudinalLayout->setCurrentWidget(speedLimitControllerPanel);

      slcOpen = false;
    }
  });
  QObject::connect(parent, &StarPilotSettingsWindow::closeSubSubSubPanel, [longitudinalLayout, weatherPanel, this]() {
    openDescriptions(forceOpenDescriptions, toggles);

    if (weatherOpen) {
      longitudinalLayout->setCurrentWidget(weatherPanel);

      weatherOpen = false;
    }
  });
  QObject::connect(parent, &StarPilotSettingsWindow::updateMetric, this, &StarPilotLongitudinalPanel::updateMetric);
}

void StarPilotLongitudinalPanel::showEvent(QShowEvent *event) {
  calibratedLateralAccelerationLabel->setText(QString::number(params.getFloat("CalibratedLateralAcceleration"), 'f', 2) + tr(" m/s²"));
  calibrationProgressLabel->setText(QString::number(params.getFloat("CalibrationProgress"), 'f', 2) + "%");

  longitudinalActuatorDelayToggle->setTitle(QString(tr("Actuator Delay (Default: %1)")).arg(QString::number(parent->longitudinalActuatorDelay, 'f', 2)));
  startAccelToggle->setTitle(QString(tr("Start Acceleration (Default: %1)")).arg(QString::number(parent->startAccel, 'f', 2)));
  stopAccelToggle->setTitle(QString(tr("Stop Acceleration (Default: %1)")).arg(QString::number(parent->stopAccel, 'f', 2)));
  stoppingDecelRateToggle->setTitle(QString(tr("Stopping Rate (Default: %1)")).arg(QString::number(parent->stoppingDecelRate, 'f', 2)));
  vEgoStartingToggle->setTitle(QString(tr("Start Speed (Default: %1)")).arg(QString::number(parent->vEgoStarting, 'f', 2)));
  vEgoStoppingToggle->setTitle(QString(tr("Stop Speed (Default: %1)")).arg(QString::number(parent->vEgoStopping, 'f', 2)));



  updateToggles();
}

void StarPilotLongitudinalPanel::updateMetric(bool metric, bool bootRun) {
  static bool previousMetric;
  if (metric != previousMetric && !bootRun) {
    double distanceConversion = metric ? FOOT_TO_METER : METER_TO_FOOT;
    double speedConversion = metric ? MILE_TO_KM : KM_TO_MILE;

    params.putIntNonBlocking("IncreasedStoppedDistance", params.getInt("IncreasedStoppedDistance") * distanceConversion);
    params.putIntNonBlocking("IncreasedStoppedDistanceLowVisibility", params.getInt("IncreasedStoppedDistanceLowVisibility") * distanceConversion);
    params.putIntNonBlocking("IncreasedStoppedDistanceRain", params.getInt("IncreasedStoppedDistanceRain") * distanceConversion);
    params.putIntNonBlocking("IncreasedStoppedDistanceRainStorm", params.getInt("IncreasedStoppedDistanceRainStorm") * distanceConversion);
    params.putIntNonBlocking("IncreasedStoppedDistanceSnow", params.getInt("IncreasedStoppedDistanceSnow") * distanceConversion);

    params.putIntNonBlocking("CESignalSpeed", params.getInt("CESignalSpeed") * speedConversion);
    params.putIntNonBlocking("CESpeed", params.getInt("CESpeed") * speedConversion);
    params.putIntNonBlocking("CESpeedLead", params.getInt("CESpeedLead") * speedConversion);
    params.putIntNonBlocking("CustomCruise", params.getInt("CustomCruise") * speedConversion);
    params.putIntNonBlocking("CustomCruiseLong", params.getInt("CustomCruiseLong") * speedConversion);
    params.putIntNonBlocking("Offset1", params.getInt("Offset1") * speedConversion);
    params.putIntNonBlocking("Offset2", params.getInt("Offset2") * speedConversion);
    params.putIntNonBlocking("Offset3", params.getInt("Offset3") * speedConversion);
    params.putIntNonBlocking("Offset4", params.getInt("Offset4") * speedConversion);
    params.putIntNonBlocking("Offset5", params.getInt("Offset5") * speedConversion);
    params.putIntNonBlocking("Offset6", params.getInt("Offset6") * speedConversion);
    params.putIntNonBlocking("Offset7", params.getInt("Offset7") * speedConversion);
    params.putIntNonBlocking("SetSpeedOffset", params.getInt("SetSpeedOffset") * speedConversion);
  }
  previousMetric = metric;

  static std::map<float, QString> imperialDistanceLabels;
  static std::map<float, QString> imperialSpeedLabels;
  static std::map<float, QString> imperialOffsetLabels;
  static std::map<float, QString> metricDistanceLabels;
  static std::map<float, QString> metricSpeedLabels;
  static std::map<float, QString> metricOffsetLabels;

  static bool labelsInitialized = false;
  if (!labelsInitialized) {
    for (int i = 0; i <= 10; ++i) {
      imperialDistanceLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" foot") : QString::number(i) + tr(" feet");
    }

    for (int i = 0; i <= 99; ++i) {
      imperialSpeedLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" mph");
    }
    for (int i = -99; i <= 99; ++i) {
      imperialOffsetLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" mph");
    }

    for (int i = 0; i <= 3; ++i) {
      metricDistanceLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" meter") : QString::number(i) + tr(" meters");
    }

    for (int i = 0; i <= 150; ++i) {
      metricSpeedLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" km/h");
    }
    for (int i = -150; i <= 150; ++i) {
      metricOffsetLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" km/h");
    }

    labelsInitialized = true;
  }

  StarPilotDualParamValueControl *ceSpeedToggle = reinterpret_cast<StarPilotDualParamValueControl*>(toggles["CESpeed"]);
  StarPilotParamValueButtonControl *ceSignal = static_cast<StarPilotParamValueButtonControl*>(toggles["CESignalSpeed"]);
  StarPilotParamValueControl *customCruiseToggle = static_cast<StarPilotParamValueControl*>(toggles["CustomCruise"]);
  StarPilotParamValueControl *customCruiseLongToggle = static_cast<StarPilotParamValueControl*>(toggles["CustomCruiseLong"]);
  StarPilotParamValueControl *offset1Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset1"]);
  StarPilotParamValueControl *offset2Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset2"]);
  StarPilotParamValueControl *offset3Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset3"]);
  StarPilotParamValueControl *offset4Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset4"]);
  StarPilotParamValueControl *offset5Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset5"]);
  StarPilotParamValueControl *offset6Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset6"]);
  StarPilotParamValueControl *offset7Toggle = static_cast<StarPilotParamValueControl*>(toggles["Offset7"]);
  StarPilotParamValueControl *increasedStoppedDistanceToggle = static_cast<StarPilotParamValueControl*>(toggles["IncreasedStoppedDistance"]);
  StarPilotParamValueControl *increasedStoppedDistanceLowVisibilityToggle = static_cast<StarPilotParamValueControl*>(toggles["IncreasedStoppedDistanceLowVisibility"]);
  StarPilotParamValueControl *increasedStoppedDistanceRainToggle = static_cast<StarPilotParamValueControl*>(toggles["IncreasedStoppedDistanceRain"]);
  StarPilotParamValueControl *increasedStoppedDistanceRainStormToggle = static_cast<StarPilotParamValueControl*>(toggles["IncreasedStoppedDistanceRainStorm"]);
  StarPilotParamValueControl *increasedStoppedDistanceSnowToggle = static_cast<StarPilotParamValueControl*>(toggles["IncreasedStoppedDistanceSnow"]);
  StarPilotParamValueControl *setSpeedOffsetToggle = static_cast<StarPilotParamValueControl*>(toggles["SetSpeedOffset"]);

  if (metric) {
    offset1Toggle->setTitle(tr("Speed Offset (0–29 km/h)"));
    offset2Toggle->setTitle(tr("Speed Offset (30–49 km/h)"));
    offset3Toggle->setTitle(tr("Speed Offset (50–59 km/h)"));
    offset4Toggle->setTitle(tr("Speed Offset (60–79 km/h)"));
    offset5Toggle->setTitle(tr("Speed Offset (80–99 km/h)"));
    offset6Toggle->setTitle(tr("Speed Offset (100–119 km/h)"));
    offset7Toggle->setTitle(tr("Speed Offset (120–140 km/h)"));

    offset1Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 0 and 24 mph."));
    offset2Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 25 and 34 mph."));
    offset3Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 35 and 44 mph."));
    offset4Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 45 and 54 mph."));
    offset5Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 55 and 64 mph."));
    offset6Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 65 and 74 mph."));
    offset7Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 75 and 99 mph."));

    increasedStoppedDistanceToggle->updateControl(0, 3, metricDistanceLabels);
    increasedStoppedDistanceLowVisibilityToggle->updateControl(0, 3, metricDistanceLabels);
    increasedStoppedDistanceRainToggle->updateControl(0, 3, metricDistanceLabels);
    increasedStoppedDistanceRainStormToggle->updateControl(0, 3, metricDistanceLabels);
    increasedStoppedDistanceSnowToggle->updateControl(0, 3, metricDistanceLabels);

    ceSignal->updateControl(0, 150, metricSpeedLabels);
    ceSpeedToggle->updateControl(0, 150, metricSpeedLabels);
    customCruiseToggle->updateControl(1, 150, metricSpeedLabels);
    customCruiseLongToggle->updateControl(1, 150, metricSpeedLabels);
    offset1Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset2Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset3Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset4Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset5Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset6Toggle->updateControl(-150, 150, metricOffsetLabels);
    offset7Toggle->updateControl(-150, 150, metricOffsetLabels);
    setSpeedOffsetToggle->updateControl(-150, 150, metricSpeedLabels);
  } else {
    offset1Toggle->setTitle(tr("Speed Offset (0–24 mph)"));
    offset2Toggle->setTitle(tr("Speed Offset (25–34 mph)"));
    offset3Toggle->setTitle(tr("Speed Offset (35–44 mph)"));
    offset4Toggle->setTitle(tr("Speed Offset (45–54 mph)"));
    offset5Toggle->setTitle(tr("Speed Offset (55–64 mph)"));
    offset6Toggle->setTitle(tr("Speed Offset (65–74 mph)"));
    offset7Toggle->setTitle(tr("Speed Offset (75–99 mph)"));

    offset1Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 0 and 24 mph."));
    offset2Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 25 and 34 mph."));
    offset3Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 35 and 44 mph."));
    offset4Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 45 and 54 mph."));
    offset5Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 55 and 64 mph."));
    offset6Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 65 and 74 mph."));
    offset7Toggle->setDescription(tr("<b>How much to offset posted speed-limits</b> between 75 and 99 mph."));

    increasedStoppedDistanceToggle->updateControl(0, 10, imperialDistanceLabels);
    increasedStoppedDistanceLowVisibilityToggle->updateControl(0, 10, imperialDistanceLabels);
    increasedStoppedDistanceRainToggle->updateControl(0, 10, imperialDistanceLabels);
    increasedStoppedDistanceRainStormToggle->updateControl(0, 10, imperialDistanceLabels);
    increasedStoppedDistanceSnowToggle->updateControl(0, 10, imperialDistanceLabels);

    ceSignal->updateControl(0, 99, imperialSpeedLabels);
    ceSpeedToggle->updateControl(0, 99, imperialSpeedLabels);
    customCruiseToggle->updateControl(1, 99, imperialSpeedLabels);
    customCruiseLongToggle->updateControl(1, 99, imperialSpeedLabels);
    offset1Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset2Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset3Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset4Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset5Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset6Toggle->updateControl(-99, 99, imperialOffsetLabels);
    offset7Toggle->updateControl(-99, 99, imperialOffsetLabels);
    setSpeedOffsetToggle->updateControl(0, 99, imperialSpeedLabels);
  }
}

void StarPilotLongitudinalPanel::updateToggles() {
  const bool showAllToggles = parent->showAllTogglesEnabled();

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      toggle->setVisible(showAllToggles);
    }
  }

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      continue;
    }

    bool setVisible = showAllToggles || parent->tuningLevel >= parent->starpilotToggleLevels[key].toDouble();

    if (!showAllToggles) {
      if (key == "CEStopLights") {
        setVisible &= parent->tuningLevel < parent->starpilotToggleLevels["CEModelStopTime"].toDouble();
      }

      else if (key == "CustomCruise" || key == "CustomCruiseLong" || key == "SetSpeedLimit" || key == "SetSpeedOffset") {
        setVisible &= !parent->hasPCMCruise;
      }

      else if (key == "HumanLaneChanges") {
        setVisible &= parent->hasRadar;
      }

      else if (key == "RadarTakeoffs") {
        setVisible &= parent->hasRadar;
      }

      else if (key == "MapGears") {
        setVisible &= parent->isToyota || parent->isHKG;
        setVisible &= !parent->isTSK;
      }

      else if (key == "ReverseCruise") {
        setVisible &= parent->isToyota;
      }

      else if (key == "SLCMapboxFiller") {
        setVisible &= !params.get("MapboxSecretKey").empty();
      }

      else if (key == "StartAccel") {
        setVisible &= !(params.getBool("LongitudinalTune") && params.getBool("HumanAcceleration"));
      }

      else if (key == "StoppingDecelRate" || key == "VEgoStarting" || key == "VEgoStopping") {
        setVisible &= !parent->isGM || !params.getBool("ExperimentalGMTune");
        setVisible &= !parent->isToyota || !params.getBool("FrogsGoMoosTweak");
      }
    }

    if (key == "EVTuning") {
      toggle->setEnabled(!params.getBool("TruckTuning"));
    } else if (key == "TruckTuning") {
      toggle->setEnabled(!params.getBool("EVTuning"));
    }

    toggle->setVisible(setVisible);

    if (setVisible) {
      if (advancedLongitudinalTuneKeys.contains(key)) {
        toggles["AdvancedLongitudinalTune"]->setVisible(true);
      } else if (aggressivePersonalityKeys.contains(key)) {
        toggles["AggressivePersonalityProfile"]->setVisible(true);
      } else if (conditionalExperimentalKeys.contains(key)) {
        toggles["ConditionalExperimental"]->setVisible(true);
      } else if (curveSpeedKeys.contains(key)) {
        toggles["CurveSpeedController"]->setVisible(true);
      } else if (customDrivingPersonalityKeys.contains(key)) {
        toggles["CustomPersonalities"]->setVisible(true);
      } else if (longitudinalTuneKeys.contains(key)) {
        toggles["LongitudinalTune"]->setVisible(true);
      } else if (qolKeys.contains(key)) {
        toggles["QOLLongitudinal"]->setVisible(true);
      } else if (relaxedPersonalityKeys.contains(key)) {
        toggles["RelaxedPersonalityProfile"]->setVisible(true);
      } else if (speedLimitControllerKeys.contains(key)) {
        toggles["SpeedLimitController"]->setVisible(true);
      } else if (speedLimitControllerOffsetsKeys.contains(key)) {
        toggles["SLCOffsets"]->setVisible(true);
      } else if (speedLimitControllerQOLKeys.contains(key)) {
        toggles["SLCQOL"]->setVisible(true);
      } else if (speedLimitControllerVisualKeys.contains(key)) {
        toggles["SLCVisuals"]->setVisible(true);
      } else if (standardPersonalityKeys.contains(key)) {
        toggles["StandardPersonalityProfile"]->setVisible(true);
      } else if (trafficPersonalityKeys.contains(key)) {
        toggles["TrafficPersonalityProfile"]->setVisible(true);
      }
    }
  }

  openDescriptions(forceOpenDescriptions, toggles);

  update();
}
