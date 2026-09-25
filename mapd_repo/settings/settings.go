package settings

import (
	"encoding/json"
	"log/slog"
	"os"
	"strings"
	"time"

	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/params"

	"github.com/Jeffail/gabs/v2"
)

const SETTINGS_VERSION = 2 // Used for migrations

var Settings = MapdSettings{
	SettingsVersion:  SETTINGS_VERSION,
	downloadProgress: make(chan DownloadProgress, 1),
	cancelDownload:   make(chan bool, 1),
}

type SpeedLimitPriority string

const (
	PRIORITY_MAP      = "map"
	PRIORITY_EXTERNAL = "external"
	PRIORITY_HIGHEST  = "highest"
	PRIORITY_LOWEST   = "lowest"
)

type MapdSettings struct {
	downloadProgress                    chan DownloadProgress
	cancelDownload                      chan bool
	downloadActive                      bool
	externalSpeedLimit                  float32
	speedLimitAccepted                  bool
	currentPersonality                  log.LongitudinalPersonality
	SettingsVersion                     float32            `json:"settings_version"`
	VisionCurveSpeedControlEnabled      bool               `json:"vision_curve_speed_control_enabled"`
	MapCurveSpeedControlEnabled         bool               `json:"map_curve_speed_control_enabled"`
	SpeedLimitControlEnabled            bool               `json:"speed_limit_control_enabled"`
	ExternalSpeedLimitControlEnabled    bool               `json:"external_speed_limit_control_enabled"`
	ConditionalSpeedLimitControlEnabled bool               `json:"conditional_speed_limit_control_enabled"`
	VisionCurveUseEnableSpeed           bool               `json:"vision_curve_use_enable_speed"`
	SpeedLimitUseEnableSpeed            bool               `json:"speed_limit_use_enable_speed"`
	MapCurveUseEnableSpeed              bool               `json:"map_curve_use_enable_speed"`
	EnableSpeed                         float32            `json:"enable_speed"`
	DefaultLaneWidth                    float32            `json:"default_lane_width"`
	SubscriberSettings                  SubscriberSettings `json:"subscriber"`
	SpeedLimitSettings                  SpeedLimitSettings `json:"speed_limit"`
	LogSettings                         LogSettings        `json:"logger"`
	Personalities                       Personalities      `json:"personalities"`
}

type SpeedLimitSettings struct {
	PressGasToAcceptSpeedLimit          bool    `json:"press_gas_to_accept_speed_limit"`
	PressGasToOverrideSpeedLimit        bool    `json:"press_gas_to_override_speed_limit"`
	AdjustSetSpeedToAcceptSpeedLimit    bool    `json:"adjust_set_speed_to_accept_speed_limit"`
	AcceptSpeedLimitTimeout             float32 `json:"accept_speed_limit_timeout"`
	SpeedLimitPriority                  string  `json:"speed_limit_priority"`
	SpeedLimitChangeRequiresAccept      bool    `json:"speed_limit_change_requires_accept"`
	HoldLastSeenSpeedLimit              bool    `json:"hold_last_seen_speed_limit"`
	HoldSpeedLimitWhileChangingSetSpeed bool    `json:"hold_speed_limit_while_changing_set_speed"`
	SpeedLimitOffset                    float32 `json:"speed_limit_offset"`
}

type LogSettings struct {
	LogLevel  string `json:"log_level"`
	LogJson   bool   `json:"log_json"`
	LogSource bool   `json:"log_source"`
}

type Personalities struct {
	Relaxed    PersonalitySettings `json:"relaxed"`
	Standard   PersonalitySettings `json:"standard"`
	Aggressive PersonalitySettings `json:"aggressive"`
}

type PersonalitySettings struct {
	TargetSpeedJerk                         float32 `json:"target_speed_jerk"`
	TargetSpeedAccel                        float32 `json:"target_speed_accel"`
	CurveTargetSpeedTimeOffset              float32 `json:"curve_target_speed_time_offset"`
	SpeedLimitIncreaseTargetSpeedTimeOffset float32 `json:"speed_limit_increase_target_speed_time_offset"`
	SpeedLimitDecreaseTargetSpeedTimeOffset float32 `json:"speed_limit_decrease_target_speed_time_offset"`
	MapCurveTargetLatA                      float32 `json:"map_curve_target_lat_a"`
	VisionCurveTargetLatA                   float32 `json:"vision_curve_target_lat_a"`
	VisionCurveMinTargetV                   float32 `json:"vision_curve_min_target_v"`
	SlowDownForNextSpeedLimit               bool    `json:"slow_down_for_next_speed_limit"`
	SpeedUpForNextSpeedLimit                bool    `json:"speed_up_for_next_speed_limit"`
}

type SubscriberSettings struct {
	ShadowCarState            bool `json:"shadow_car_state"`
	ShadowModelV2             bool `json:"shadow_model_v2"`
	ShadowGpsLocation         bool `json:"shadow_gps_location"`
	ShadowGpsLocationExternal bool `json:"shadow_gps_location_external"`
	ShadowSelfdriveState      bool `json:"shadow_selfdrive_state"`
}

func (s *MapdSettings) Default() {
	err := json.Unmarshal(defaultsJson, s) // load included default settings first to ensure all values have a default
	if err != nil {
		slog.Warn("failed to load default settings", "error", err)
		return
	}

	// overwrite default values with custom defaults
	if _, err := os.Stat("/data/openpilot/mapd_defaults.json"); err == nil {
		defaults, err := os.ReadFile("/data/openpilot/mapd_defaults.json")
		if err != nil {
			slog.Warn("failed to read custom default settings", "error", err)
		}

		parsed, err := gabs.ParseJSON(defaults)
		if err != nil {
			slog.Warn("failed to parse custom default settings", "error", err)
		}

		settingsVersion := parsed.S("settings_version").Data()
		if settingsVersion == nil {
			settingsVersion = uint64(0)
		}

		if settingsVersion != SETTINGS_VERSION {
			slog.Info("default file settings version mismatch, running migrations", "expected_version", SETTINGS_VERSION, "settings_version", settingsVersion)
			migratedSettings := Migrate(uint64(settingsVersion.(uint64)), defaults)
			defaults, err = json.Marshal(migratedSettings)
			if err != nil {
				slog.Warn("failed to marshal migrated default settings", "error", err)
				return
			}
		}

		err = json.Unmarshal(defaults, s)
		if err != nil {
			slog.Warn("failed to load custom default settings", "error", err)
			return
		}
	}
}

// BundledDefaults decodes only the embedded defaults. Diagnostic observation
// must not read device-specific /data overrides or persistent settings.
func BundledDefaults() (MapdSettings, error) {
	defaults := MapdSettings{
		SettingsVersion:  SETTINGS_VERSION,
		downloadProgress: make(chan DownloadProgress, 1),
		cancelDownload:   make(chan bool, 1),
	}
	err := json.Unmarshal(defaultsJson, &defaults)
	return defaults, err
}

func (s *MapdSettings) Recommended() {
	if _, err := os.Stat("/data/openpilot/mapd_recommended.json"); err == nil {
		recommended, err := os.ReadFile("/data/openpilot/mapd_recommended.json")
		if err != nil {
			slog.Warn("failed to read custom recommended settings", "error", err)
		}

		parsed, err := gabs.ParseJSON(recommended)
		if err != nil {
			slog.Warn("failed to parse custom recommended settings", "error", err)
		}

		settingsVersion := parsed.S("settings_version").Data()
		if settingsVersion == nil {
			settingsVersion = uint64(0)
		}

		if settingsVersion != SETTINGS_VERSION {
			slog.Info("default file settings version mismatch, running migrations", "expected_version", SETTINGS_VERSION, "settings_version", settingsVersion)
			migratedSettings := Migrate(uint64(settingsVersion.(uint64)), recommended)
			recommended, err = json.Marshal(migratedSettings)
			if err != nil {
				slog.Warn("failed to marshal migrated recommended settings", "error", err)
				return
			}
		}

		err = json.Unmarshal(recommended, s)
		if err != nil {
			slog.Warn("failed to load custom recommended settings", "error", err)
			return
		}
	} else {
		err := json.Unmarshal(recommendedJson, s)
		if err != nil {
			slog.Warn("failed to load recommended settings", "error", err)
		}
	}
}

func (s *MapdSettings) Load() (success bool) {
	data, err := params.GetParam(params.MAPD_SETTINGS)
	if err != nil {
		slog.Warn("failed to read MAPD_SETTINGS param", "error", err)
		return false
	}

	parsed, err := gabs.ParseJSON(data)
	if err != nil {
		slog.Warn("failed to parse MAPD_SETTINGS json", "error", err)
		return false
	}

	settingsVersion := parsed.S("settings_version").Data()
	if settingsVersion == nil {
		settingsVersion = float64(0)
	}

	if settingsVersion.(float64) != float64(SETTINGS_VERSION) {
		slog.Info("settings version mismatch, running migrations", "expected_version", SETTINGS_VERSION, "settings_version", settingsVersion)
		migratedSettings := Migrate(uint64(settingsVersion.(float64)), data)
		data, err = json.Marshal(migratedSettings)
		if err != nil {
			slog.Warn("failed to marshal migrated settings", "error", err)
			return false
		}
	}
	err = json.Unmarshal(data, s)
	if err != nil {
		slog.Warn("failed to parse MAPD_SETTINGS param", "error", err)
		return false
	}

	s.setupLogger()

	return true
}

func (s *MapdSettings) LoadChanges(data *gabs.Container) (success bool) {
	jsonString := data.Bytes()
	err := json.Unmarshal(jsonString, s)
	if err != nil {
		slog.Warn("failed to parse updated settings json", "error", err)
		return false
	}

	s.setupLogger()

	return true
}

func (s *MapdSettings) Unmarshal(b []byte) (success bool) {
	s.Default() // set defaults so settings not already in param are defaulted
	err := json.Unmarshal(b, s)
	if err != nil {
		slog.Warn("failed to unmarshal settings data", "error", err)
		return false
	}

	s.setupLogger()

	return true
}

func (s *MapdSettings) LoadWithRetries(tries int) {
	for range tries {
		if s.Load() {
			break
		}
		time.Sleep(1 * time.Second)
	}
	s.Save()
}

func (s *MapdSettings) Save() {
	s.SettingsVersion = SETTINGS_VERSION
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		slog.Error("failed to marshal settings to json", "error", err)
		return
	}
	err = params.PutParam(params.MAPD_SETTINGS, data)
	if err != nil {
		slog.Error("failed to save MAPD_SETTINGS param", "error", err)
		return
	}
}

func (s *MapdSettings) setupLogger() {
	handlerOptions := slog.HandlerOptions{
		AddSource: s.LogSettings.LogSource,
	}
	if s.LogSettings.LogJson {
		slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &handlerOptions)))
	} else {
		slog.SetDefault(slog.New(slog.NewTextHandler(os.Stdout, &handlerOptions)))
	}
	s.setLogLevel()
}

func (s *MapdSettings) setLogLevel() {
	switch strings.ToLower(s.LogSettings.LogLevel) {
	case "debug":
		slog.SetLogLoggerLevel(slog.LevelDebug)
	case "info":
		slog.SetLogLoggerLevel(slog.LevelInfo)
	case "warn":
		slog.SetLogLoggerLevel(slog.LevelWarn)
	case "error":
		slog.SetLogLoggerLevel(slog.LevelError)
	default:
		slog.SetLogLoggerLevel(slog.LevelError)
	}
}

func (s *MapdSettings) GetDownloadProgress() (progress DownloadProgress, success bool) {
	select {
	case progress = <-s.downloadProgress:
		s.downloadActive = progress.Active
		return progress, true
	default:
	}
	return
}

func (s *MapdSettings) ExternalSpeedLimit() float32 {
	return s.externalSpeedLimit
}

func (s *MapdSettings) Handle(input custom.MapdIn) {
	switch input.Type() {
	case custom.MapdInputType_reloadSettings:
		s.Default()
		s.Load()
	case custom.MapdInputType_saveSettings:
		s.SettingsVersion = SETTINGS_VERSION
		settingsSnapshot := *s
		go settingsSnapshot.Save()
	case custom.MapdInputType_loadPersistentSettings:
		s.Load()
	case custom.MapdInputType_loadDefaultSettings:
		s.Default()
	case custom.MapdInputType_loadRecommendedSettings:
		s.Recommended()
	case custom.MapdInputType_cancelDownload:
		select {
		case s.cancelDownload <- true:
		default:
		}
	case custom.MapdInputType_download:
		path, err := input.Str()
		if err != nil {
			slog.Warn("failed to read download path string", "error", err)
			return
		}
		if !s.downloadActive {
			go Download(path, s.downloadProgress, s.cancelDownload)
		}
	case custom.MapdInputType_acceptSpeedLimit:
		s.AcceptSpeedLimit()
	case custom.MapdInputType_setJsonPathBool:
		s.setSetting(input)
	case custom.MapdInputType_setJsonPathFloat:
		s.setSetting(input)
	case custom.MapdInputType_setJsonPathText:
		s.setSetting(input)

	// DEPRECATED settings inputs
	case custom.MapdInputType_setVisionCurveMinTargetV:
		s.Personalities.Aggressive.VisionCurveMinTargetV = input.Float()
		s.Personalities.Relaxed.VisionCurveMinTargetV = input.Float()
		s.Personalities.Standard.VisionCurveMinTargetV = input.Float()
	case custom.MapdInputType_setVisionCurveTargetLatA:
		s.Personalities.Aggressive.VisionCurveTargetLatA = input.Float()
		s.Personalities.Relaxed.VisionCurveTargetLatA = input.Float()
		s.Personalities.Standard.VisionCurveTargetLatA = input.Float()
	case custom.MapdInputType_setVisionCurveSpeedControl:
		s.VisionCurveSpeedControlEnabled = input.Bool()
	case custom.MapdInputType_setSpeedLimitControl:
		s.SpeedLimitControlEnabled = input.Bool()
	case custom.MapdInputType_setConditionalSpeedLimitControl:
		s.ConditionalSpeedLimitControlEnabled = input.Bool()
	case custom.MapdInputType_setMapCurveSpeedControl:
		s.MapCurveSpeedControlEnabled = input.Bool()
	case custom.MapdInputType_setSpeedLimitOffset:
		s.SpeedLimitSettings.SpeedLimitOffset = input.Float()
	case custom.MapdInputType_setEnableSpeed:
		s.EnableSpeed = input.Float()
	case custom.MapdInputType_setVisionCurveUseEnableSpeed:
		s.VisionCurveUseEnableSpeed = input.Bool()
	case custom.MapdInputType_setMapCurveUseEnableSpeed:
		s.MapCurveUseEnableSpeed = input.Bool()
	case custom.MapdInputType_setSpeedLimitUseEnableSpeed:
		s.SpeedLimitUseEnableSpeed = input.Bool()
	case custom.MapdInputType_setHoldLastSeenSpeedLimit:
		s.SpeedLimitSettings.HoldLastSeenSpeedLimit = input.Bool()
	case custom.MapdInputType_setTargetSpeedJerk:
		s.Personalities.Aggressive.TargetSpeedJerk = input.Float()
		s.Personalities.Relaxed.TargetSpeedJerk = input.Float()
		s.Personalities.Standard.TargetSpeedJerk = input.Float()
	case custom.MapdInputType_setTargetSpeedAccel:
		s.Personalities.Aggressive.TargetSpeedAccel = input.Float()
		s.Personalities.Relaxed.TargetSpeedAccel = input.Float()
		s.Personalities.Standard.TargetSpeedAccel = input.Float()
	case custom.MapdInputType_setTargetSpeedTimeOffset:
		s.Personalities.Aggressive.CurveTargetSpeedTimeOffset = input.Float()
		s.Personalities.Relaxed.CurveTargetSpeedTimeOffset = input.Float()
		s.Personalities.Standard.CurveTargetSpeedTimeOffset = input.Float()
		s.Personalities.Aggressive.SpeedLimitIncreaseTargetSpeedTimeOffset = input.Float()
		s.Personalities.Relaxed.SpeedLimitIncreaseTargetSpeedTimeOffset = input.Float()
		s.Personalities.Standard.SpeedLimitIncreaseTargetSpeedTimeOffset = input.Float()
		s.Personalities.Aggressive.SpeedLimitDecreaseTargetSpeedTimeOffset = input.Float()
		s.Personalities.Relaxed.SpeedLimitDecreaseTargetSpeedTimeOffset = input.Float()
		s.Personalities.Standard.SpeedLimitDecreaseTargetSpeedTimeOffset = input.Float()
	case custom.MapdInputType_setDefaultLaneWidth:
		s.DefaultLaneWidth = input.Float()
	case custom.MapdInputType_setMapCurveTargetLatA:
		s.Personalities.Aggressive.MapCurveTargetLatA = input.Float()
		s.Personalities.Relaxed.MapCurveTargetLatA = input.Float()
		s.Personalities.Standard.MapCurveTargetLatA = input.Float()
	case custom.MapdInputType_setExternalSpeedLimitControl:
		s.ExternalSpeedLimitControlEnabled = input.Bool()
	case custom.MapdInputType_setSpeedLimitPriority:
		priority, err := input.Str()
		if err != nil {
			slog.Warn("failed to read speed limit priority string", "error", err)
			return
		}
		s.SpeedLimitSettings.SpeedLimitPriority = priority
	case custom.MapdInputType_setExternalSpeedLimit:
		s.externalSpeedLimit = input.Float()
	case custom.MapdInputType_setHoldSpeedLimitWhileChangingSetSpeed:
		s.SpeedLimitSettings.HoldSpeedLimitWhileChangingSetSpeed = input.Bool()
	case custom.MapdInputType_setSpeedUpForNextSpeedLimit:
		s.Personalities.Aggressive.SpeedUpForNextSpeedLimit = input.Bool()
		s.Personalities.Relaxed.SpeedUpForNextSpeedLimit = input.Bool()
		s.Personalities.Standard.SpeedUpForNextSpeedLimit = input.Bool()
	case custom.MapdInputType_setSlowDownForNextSpeedLimit:
		s.Personalities.Aggressive.SlowDownForNextSpeedLimit = input.Bool()
		s.Personalities.Relaxed.SlowDownForNextSpeedLimit = input.Bool()
		s.Personalities.Standard.SlowDownForNextSpeedLimit = input.Bool()
	case custom.MapdInputType_setSpeedLimitChangeRequiresAccept:
		s.SpeedLimitSettings.SpeedLimitChangeRequiresAccept = input.Bool()
	case custom.MapdInputType_setPressGasToAcceptSpeedLimit:
		s.SpeedLimitSettings.PressGasToAcceptSpeedLimit = input.Bool()
	case custom.MapdInputType_setPressGasToOverrideSpeedLimit:
		s.SpeedLimitSettings.PressGasToOverrideSpeedLimit = input.Bool()
	case custom.MapdInputType_setShadowCarState:
		s.SubscriberSettings.ShadowCarState = input.Bool()
	case custom.MapdInputType_setShadowModelV2:
		s.SubscriberSettings.ShadowModelV2 = input.Bool()
	case custom.MapdInputType_setShadowGpsLocation:
		s.SubscriberSettings.ShadowGpsLocation = input.Bool()
	case custom.MapdInputType_setShadowGpsLocationExternal:
		s.SubscriberSettings.ShadowGpsLocationExternal = input.Bool()
	case custom.MapdInputType_setAdjustSetSpeedToAcceptSpeedLimit:
		s.SpeedLimitSettings.AdjustSetSpeedToAcceptSpeedLimit = input.Bool()
	case custom.MapdInputType_setAcceptSpeedLimitTimeout:
		s.SpeedLimitSettings.AcceptSpeedLimitTimeout = input.Float()
	case custom.MapdInputType_setLogLevel:
		logLevel, err := input.Str()
		if err != nil {
			slog.Warn("failed to read log level string", "error", err)
			return
		}
		s.LogSettings.LogLevel = logLevel
		s.setLogLevel()
	case custom.MapdInputType_setLogSource:
		s.LogSettings.LogSource = input.Bool()
		s.setupLogger()
	case custom.MapdInputType_setLogJson:
		s.LogSettings.LogJson = input.Bool()
		s.setupLogger()
	}
}

func (s *MapdSettings) PrioritySpeedLimit(mapLimit float32) float32 {
	if s.SpeedLimitControlEnabled && !s.ExternalSpeedLimitControlEnabled {
		return mapLimit
	}
	if s.ExternalSpeedLimitControlEnabled && !s.SpeedLimitControlEnabled {
		return s.externalSpeedLimit
	}
	if !s.SpeedLimitControlEnabled && !s.ExternalSpeedLimitControlEnabled {
		return 0
	}
	switch s.SpeedLimitSettings.SpeedLimitPriority {
	case PRIORITY_MAP:
		if mapLimit == 0 {
			return s.externalSpeedLimit
		}
		return mapLimit
	case PRIORITY_EXTERNAL:
		if s.externalSpeedLimit == 0 {
			return mapLimit
		}
		return s.externalSpeedLimit
	case PRIORITY_HIGHEST:
		return max(mapLimit, s.externalSpeedLimit)
	case PRIORITY_LOWEST:
		if mapLimit == 0 {
			return s.externalSpeedLimit
		}
		if s.externalSpeedLimit == 0 {
			return mapLimit
		}
		return min(mapLimit, s.externalSpeedLimit)
	default:
		if mapLimit == 0 {
			return s.externalSpeedLimit
		}
		return mapLimit
	}
}

func (s *MapdSettings) setSetting(input custom.MapdIn) {
	data, err := json.Marshal(s)
	if err != nil {
		slog.Error("failed to marshal settings to json", "error", err)
		return
	}
	jsonParsed, err := gabs.ParseJSON(data)
	if err != nil {
		slog.Error("failed to parse settings json", "error", err)
		return
	}
	path, err := input.JsonPath()
	if err != nil {
		slog.Error("failed to read json path string", "error", err)
		return
	}
	var value any = nil
	switch input.Type() {
	case custom.MapdInputType_setJsonPathText:
		textVal, err := input.Str()
		if err != nil {
			slog.Error("failed to read text value string", "error", err)
			return
		}
		value = textVal
	case custom.MapdInputType_setJsonPathBool:
		value = input.Bool()
	case custom.MapdInputType_setJsonPathFloat:
		value = input.Float()
	}
	_, err = jsonParsed.SetP(value, path)
	if err != nil {
		slog.Error("failed to set value at json path", "error", err)
		return
	}

	s.LoadChanges(jsonParsed)
}

func (s *MapdSettings) ResetSpeedLimitAccepted() {
	s.speedLimitAccepted = false
}

func (s *MapdSettings) SpeedLimitAccepted() bool {
	if !s.SpeedLimitSettings.SpeedLimitChangeRequiresAccept {
		return true
	}
	return s.speedLimitAccepted
}

func (s *MapdSettings) AcceptSpeedLimit() {
	s.speedLimitAccepted = true
}

func (s *MapdSettings) SetPersonality(p log.LongitudinalPersonality) {
	s.currentPersonality = p
}

func (s *MapdSettings) CurrentPersonality() PersonalitySettings {
	switch s.currentPersonality {
	case log.LongitudinalPersonality_aggressive:
		return s.Personalities.Aggressive
	case log.LongitudinalPersonality_relaxed:
		return s.Personalities.Relaxed
	default:
		return s.Personalities.Standard
	}
}
