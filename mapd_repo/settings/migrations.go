package settings

import (
	"encoding/json"
	"log/slog"
)

func Migrate(version uint64, jsonString []byte) MapdSettings {
	var migratedSettings any

	switch version {
	case 1:
		var v1Settings V1Settings
		err := json.Unmarshal(jsonString, &v1Settings)
		if err != nil {
			slog.Error("Error unmarshalling V1 settings: %v", "error", err)
			return MapdSettings{}
		}
		migratedSettings = v1Settings
	}

	if version == 1 {
		v1Settings := migratedSettings.(V1Settings)
		migratedSettings = v2(v1Settings)
		version = 2
	}

	return migratedSettings.(MapdSettings)
}

func v2(v1Settings V1Settings) MapdSettings {
	personalitySettings := PersonalitySettings{
		TargetSpeedJerk:                         v1Settings.TargetSpeedJerk,
		TargetSpeedAccel:                        v1Settings.TargetSpeedAccel,
		CurveTargetSpeedTimeOffset:              v1Settings.TargetSpeedTimeOffset,
		SpeedLimitIncreaseTargetSpeedTimeOffset: v1Settings.TargetSpeedTimeOffset,
		SpeedLimitDecreaseTargetSpeedTimeOffset: v1Settings.TargetSpeedTimeOffset,
		VisionCurveTargetLatA:                   v1Settings.VisionCurveTargetLatA,
		VisionCurveMinTargetV:                   v1Settings.VisionCurveMinTargetV,
		MapCurveTargetLatA:                      v1Settings.MapCurveTargetLatA,
		SlowDownForNextSpeedLimit:               v1Settings.SlowDownForNextSpeedLimit,
		SpeedUpForNextSpeedLimit:                v1Settings.SpeedUpForNextSpeedLimit,
	}

	v2Settings := MapdSettings{
		SettingsVersion:                  2,
		VisionCurveSpeedControlEnabled:   v1Settings.VisionCurveSpeedControlEnabled,
		MapCurveSpeedControlEnabled:      v1Settings.MapCurveSpeedControlEnabled,
		SpeedLimitControlEnabled:         v1Settings.SpeedLimitControlEnabled,
		ExternalSpeedLimitControlEnabled: v1Settings.ExternalSpeedLimitControlEnabled,
		VisionCurveUseEnableSpeed:        v1Settings.VisionCurveUseEnableSpeed,
		SpeedLimitUseEnableSpeed:         v1Settings.SpeedLimitUseEnableSpeed,
		MapCurveUseEnableSpeed:           v1Settings.MapCurveUseEnableSpeed,
		EnableSpeed:                      v1Settings.EnableSpeed,
		DefaultLaneWidth:                 v1Settings.DefaultLaneWidth,
		SubscriberSettings: SubscriberSettings{
			ShadowCarState:            true,
			ShadowModelV2:             false,
			ShadowGpsLocation:         false,
			ShadowGpsLocationExternal: false,
			ShadowSelfdriveState:      false,
		},
		LogSettings: LogSettings{
			LogLevel:  v1Settings.LogLevel,
			LogJson:   v1Settings.LogJson,
			LogSource: v1Settings.LogSource,
		},
		Personalities: Personalities{
			Standard:   personalitySettings,
			Relaxed:    personalitySettings,
			Aggressive: personalitySettings,
		},
		SpeedLimitSettings: SpeedLimitSettings{
			PressGasToAcceptSpeedLimit:          v1Settings.PressGasToAcceptSpeedLimit,
			PressGasToOverrideSpeedLimit:        v1Settings.PressGasToOverrideSpeedLimit,
			AdjustSetSpeedToAcceptSpeedLimit:    v1Settings.AdjustSetSpeedToAcceptSpeedLimit,
			AcceptSpeedLimitTimeout:             v1Settings.AcceptSpeedLimitTimeout,
			SpeedLimitPriority:                  v1Settings.SpeedLimitPriority,
			SpeedLimitChangeRequiresAccept:      v1Settings.SpeedLimitChangeRequiresAccept,
			SpeedLimitOffset:                    v1Settings.SpeedLimitOffset,
			HoldLastSeenSpeedLimit:              v1Settings.HoldLastSeenSpeedLimit,
			HoldSpeedLimitWhileChangingSetSpeed: v1Settings.HoldSpeedLimitWhileChangingSetSpeed,
		},
	}
	return v2Settings
}

type V1Settings struct {
	SettingsVersion                     float32 `json:"settings_version"`
	PressGasToAcceptSpeedLimit          bool    `json:"press_gas_to_accept_speed_limit"`
	PressGasToOverrideSpeedLimit        bool    `json:"press_gas_to_override_speed_limit"`
	AdjustSetSpeedToAcceptSpeedLimit    bool    `json:"adjust_set_speed_to_accept_speed_limit"`
	AcceptSpeedLimitTimeout             float32 `json:"accept_speed_limit_timeout"`
	VisionCurveSpeedControlEnabled      bool    `json:"vision_curve_speed_control_enabled"`
	MapCurveSpeedControlEnabled         bool    `json:"map_curve_speed_control_enabled"`
	SpeedLimitControlEnabled            bool    `json:"speed_limit_control_enabled"`
	ExternalSpeedLimitControlEnabled    bool    `json:"external_speed_limit_control_enabled"`
	SpeedLimitPriority                  string  `json:"speed_limit_priority"`
	VisionCurveUseEnableSpeed           bool    `json:"vision_curve_use_enable_speed"`
	SpeedLimitUseEnableSpeed            bool    `json:"speed_limit_use_enable_speed"`
	SpeedLimitChangeRequiresAccept      bool    `json:"speed_limit_change_requires_accept"`
	MapCurveUseEnableSpeed              bool    `json:"map_curve_use_enable_speed"`
	LogLevel                            string  `json:"log_level"`
	LogJson                             bool    `json:"log_json"`
	LogSource                           bool    `json:"log_source"`
	VisionCurveTargetLatA               float32 `json:"vision_curve_target_lat_a"`
	VisionCurveMinTargetV               float32 `json:"vision_curve_min_target_v"`
	SpeedLimitOffset                    float32 `json:"speed_limit_offset"`
	EnableSpeed                         float32 `json:"enable_speed"`
	HoldLastSeenSpeedLimit              bool    `json:"hold_last_seen_speed_limit"`
	TargetSpeedJerk                     float32 `json:"target_speed_jerk"`
	TargetSpeedAccel                    float32 `json:"target_speed_accel"`
	TargetSpeedTimeOffset               float32 `json:"target_speed_time_offset"`
	DefaultLaneWidth                    float32 `json:"default_lane_width"`
	MapCurveTargetLatA                  float32 `json:"map_curve_target_lat_a"`
	SlowDownForNextSpeedLimit           bool    `json:"slow_down_for_next_speed_limit"`
	SpeedUpForNextSpeedLimit            bool    `json:"speed_up_for_next_speed_limit"`
	HoldSpeedLimitWhileChangingSetSpeed bool    `json:"hold_speed_limit_while_changing_set_speed"`
}
