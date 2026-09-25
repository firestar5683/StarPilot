package cli

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/charmbracelet/bubbles/list"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"pfeifer.dev/mapd/cereal/custom"
	ms "pfeifer.dev/mapd/settings"
)

var settingsList = []list.Item{
	settingsItem{
		title:       "Speed Limit Control Enabled",
		desc:        "When enabled mapd will use the speed limit to determine a suggested speed",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "speed_limit_control_enabled",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitControlEnabled) },
	},
	settingsItem{
		title:       "Map Curve Speed Control Enabled",
		desc:        "When enabled mapd will use map based curvature calculations to determine a suggested speed",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "map_curve_speed_control_enabled",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.MapCurveSpeedControlEnabled) },
	},
	settingsItem{
		title:       "Vision Curve Speed Control Enabled",
		desc:        "When enabled mapd will use vision model based curvature calculations to determine a suggested speed",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "vision_curve_speed_control_enabled",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.VisionCurveSpeedControlEnabled) },
	},
	settingsItem{
		title:       "External Speed Limit Control Enabled",
		desc:        "When enabled mapd will use fork provided speed limits to determine a suggested speed",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "external_speed_limit_control_enabled",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.ExternalSpeedLimitControlEnabled) },
	},
	settingsItem{
		title:       "Set Speed Limit Priority",
		desc:        "Sets the prioritization method for available speed limits",
		MessageType: custom.MapdInputType_setJsonPathText,
		Type:        Options,
		state:       settingsInput,
		jsonPath:    "speed_limit.speed_limit_priority",
		options: []list.Item{
			settingsItem{title: "map", value: func() string { return "" }},
			settingsItem{title: "external", value: func() string { return "" }},
			settingsItem{title: "highest", value: func() string { return "" }},
			settingsItem{title: "lowest", value: func() string { return "" }},
		},
		value: func() string { return fmt.Sprintf("%s", ms.Settings.SpeedLimitSettings.SpeedLimitPriority) },
	},
	settingsItem{
		title:       "Speed Limit Offset",
		desc:        "The offset that gets applied to a speed limit to determine a target speed",
		MessageType: custom.MapdInputType_setJsonPathFloat,
		Type:        Speed,
		state:       unitsInput,
		jsonPath:    "speed_limit.speed_limit_offset",
		value: func() string {
			val := ms.Settings.SpeedLimitSettings.SpeedLimitOffset
			mph := ms.MS_TO_MPH * val
			kph := ms.MS_TO_KPH * val
			return fmt.Sprintf("%f m/s, %f mph, %f kph", val, mph, kph)
		},
	},
	settingsItem{
		title:       "Speed Limit Change Requires Accept",
		desc:        "Requires user acceptance of any speed limit changes before activating",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.speed_limit_change_requires_accept",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.SpeedLimitChangeRequiresAccept) },
	},
	settingsItem{
		title:       "Press Gas To Accept Speed Limit",
		desc:        "Pressing the gas will accept a speed limit change",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.press_gas_to_accept_speed_limit",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.PressGasToAcceptSpeedLimit) },
	},
	settingsItem{
		title:       "Press Gas To Override Speed Limit",
		desc:        "Pressing the gas will override the speed limit to hold the current speed. Resets when the speed limit changes",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.press_gas_to_override_speed_limit",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.PressGasToOverrideSpeedLimit) },
	},
	settingsItem{
		title:       "Adjust Set Speed To Accept Speed Limit",
		desc:        "Adjusting the set speed once in either direction will accept a speed limit change. Additional set speed changes reject the speed limit",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.adjust_set_speed_to_accept_speed_limit",
		value: func() string {
			return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.AdjustSetSpeedToAcceptSpeedLimit)
		},
	},
	settingsItem{
		title:       "Accept Speed Limit Timeout (s)",
		desc:        "The amount of time after a speed limit change is detected that accept inputs will be used. 0 is no limit",
		MessageType: custom.MapdInputType_setJsonPathFloat,
		Type:        Float,
		state:       settingsInput,
		jsonPath:    "speed_limit.accept_speed_limit_timeout",
		value:       func() string { return fmt.Sprintf("%f", ms.Settings.SpeedLimitSettings.AcceptSpeedLimitTimeout) },
	},
	settingsItem{
		title:       "Mapd Enable Speed",
		desc:        "The speed you can set your cruise control to that will then cause mapd features to engage",
		MessageType: custom.MapdInputType_setJsonPathFloat,
		Type:        Speed,
		state:       unitsInput,
		jsonPath:    "enable_speed",
		value: func() string {
			val := ms.Settings.EnableSpeed
			mph := ms.MS_TO_MPH * val
			kph := ms.MS_TO_KPH * val
			return fmt.Sprintf("%f m/s, %f mph, %f kph", val, mph, kph)
		},
	},
	settingsItem{
		title:       "Use Enable Speed For Speed Limit",
		desc:        "Determines whether the Mapd Enable Speed controls enabling of Speed Limit Control",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit_use_enable_speed",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitUseEnableSpeed) },
	},
	settingsItem{
		title:       "Use Enable Speed for Map Curve Speed Control",
		desc:        "Determines whether the Mapd Enable Speed controls enabling of Curve Speed Control",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "map_curve_use_enable_speed",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.MapCurveUseEnableSpeed) },
	},
	settingsItem{
		title:       "Use Enable Speed for Vision Curve Speed Control",
		desc:        "Determines whether the Mapd Enable Speed controls enabling of Vision Curve Speed Control",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "vision_curve_use_enable_speed",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.VisionCurveUseEnableSpeed) },
	},
	settingsItem{
		title:       "Hold Speed Limit While Changing Set Speed",
		desc:        "When enabled mapd will suggest using the speed limit while the cruise control speed is changing. This prevents speeding up while trying to reach the enable speed",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.hold_speed_limit_while_changing_set_speed",
		value: func() string {
			return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.HoldSpeedLimitWhileChangingSetSpeed)
		},
	},
	settingsItem{
		title:       "Hold Last Seen Speed Limit",
		desc:        "When enabled mapd will use the last seen speed limit if it cannot determine a current speed limit",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "speed_limit.hold_last_seen_speed_limit",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SpeedLimitSettings.HoldLastSeenSpeedLimit) },
	},
	settingsItem{
		title:       "Default Lane Width",
		desc:        "The default lane width to use when determining if we are currently on a road",
		MessageType: custom.MapdInputType_setJsonPathFloat,
		Type:        Float,
		state:       settingsInput,
		jsonPath:    "default_lane_width",
		value:       func() string { return fmt.Sprintf("%f meters", ms.Settings.DefaultLaneWidth) },
	},
	settingsItem{
		title: "Personalities",
		desc:  "Configure per-personality settings for relaxed, standard, and aggressive driving",
		state: showPersonalitiesMenu,
		value: func() string { return "" },
	},
	settingsItem{
		title:       "Set Log Level",
		desc:        "Modify how verbose logging will be for the mapd system",
		MessageType: custom.MapdInputType_setJsonPathText,
		Type:        Options,
		state:       settingsInput,
		jsonPath:    "logger.log_level",
		options: []list.Item{
			settingsItem{title: "error", value: func() string { return "" }},
			settingsItem{title: "warn", value: func() string { return "" }},
			settingsItem{title: "info", value: func() string { return "" }},
			settingsItem{title: "debug", value: func() string { return "" }},
		},
		value: func() string { return fmt.Sprintf("%s", ms.Settings.LogSettings.LogLevel) },
	},
	settingsItem{
		title:       "Use JSON Logger",
		desc:        "When true the logs will be output in a json format instead of a text format",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "logger.log_json",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.LogSettings.LogJson) },
	},
	settingsItem{
		title:       "Log Source Location",
		desc:        "When true the logs will include the file and line that wrote the log",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Bool,
		state:       settingsInput,
		jsonPath:    "logger.log_source",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.LogSettings.LogSource) },
	},
	settingsItem{
		title: "Subscriber Settings",
		desc:  "Configure shadow-mode settings for openpilot message subscribers",
		state: showSubscribersMenu,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Load Default Settings",
		desc:  "Loads the default settings",
		state: defaultSettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Load Recommended Settings",
		desc:  "Loads the recommended settings",
		state: recommendedSettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Save Settings",
		desc:  "Persists any updates to the settings across reboots",
		state: saveSettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Return to Main Menu",
		desc:  "Exit settings configuration and return to the initial actions menu",
		state: settingsExit,
		value: func() string { return "" },
	},
}

var subscribersList = []list.Item{
	settingsItem{
		title:       "Shadow Car State",
		desc:        "Shadow the carState subscriber. Requires restart to take effect. Only enable if all subscriber slots are used and mapd is causing resets of the message queue",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "subscriber.shadow_car_state",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SubscriberSettings.ShadowCarState) },
	},
	settingsItem{
		title:       "Shadow Model V2",
		desc:        "Shadow the modelV2 subscriber. Requires restart to take effect. Only enable if all subscriber slots are used and mapd is causing resets of the message queue",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "subscriber.shadow_model_v2",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SubscriberSettings.ShadowModelV2) },
	},
	settingsItem{
		title:       "Shadow GPS Location",
		desc:        "Shadow the gpsLocation subscriber. Requires restart to take effect. Only enable if all subscriber slots are used and mapd is causing resets of the message queue",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "subscriber.shadow_gps_location",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SubscriberSettings.ShadowGpsLocation) },
	},
	settingsItem{
		title:       "Shadow GPS Location External",
		desc:        "Shadow the gpsLocationExternal subscriber. Requires restart to take effect. Only enable if all subscriber slots are used and mapd is causing resets of the message queue",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "subscriber.shadow_gps_location_external",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SubscriberSettings.ShadowGpsLocationExternal) },
	},
	settingsItem{
		title:       "Shadow Selfdrive State",
		desc:        "Shadow the selfdriveState subscriber. Requires restart to take effect. Only enable if all subscriber slots are used and mapd is causing resets of the message queue",
		MessageType: custom.MapdInputType_setJsonPathBool,
		Type:        Enable,
		state:       settingsInput,
		jsonPath:    "subscriber.shadow_selfdrive_state",
		value:       func() string { return fmt.Sprintf("%t", ms.Settings.SubscriberSettings.ShadowSelfdriveState) },
	},
	settingsItem{
		title: "Back to Settings",
		desc:  "Return to the main settings menu",
		state: showSettingsMenu,
		value: func() string { return "" },
	},
}

var personalitiesList = []list.Item{
	settingsItem{
		title: "Relaxed",
		desc:  "Configure settings for the relaxed driving personality",
		state: showPersonalitySettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Standard",
		desc:  "Configure settings for the standard driving personality",
		state: showPersonalitySettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Aggressive",
		desc:  "Configure settings for the aggressive driving personality",
		state: showPersonalitySettings,
		value: func() string { return "" },
	},
	settingsItem{
		title: "Back to Settings",
		desc:  "Return to the main settings menu",
		state: showSettingsMenu,
		value: func() string { return "" },
	},
}

func getPersonalitySettingsList(personality string) []list.Item {
	jsonPrefix := "personalities." + personality + "."

	var p *ms.PersonalitySettings
	switch personality {
	case "relaxed":
		p = &ms.Settings.Personalities.Relaxed
	case "standard":
		p = &ms.Settings.Personalities.Standard
	case "aggressive":
		p = &ms.Settings.Personalities.Aggressive
	}

	return []list.Item{
		settingsItem{
			title:       "Target Speed Jerk (m/s^3)",
			desc:        "The target amount of jerk to use when determining speed change activation distance (map curve and speed limit)",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "target_speed_jerk",
			value:       func() string { return fmt.Sprintf("%f m/s^3", p.TargetSpeedJerk) },
		},
		settingsItem{
			title:       "Target Speed Accel (m/s^2)",
			desc:        "The target amount of acceleration to use when determining speed change activation distance (map curve and speed limit)",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "target_speed_accel",
			value:       func() string { return fmt.Sprintf("%f m/s^2", p.TargetSpeedAccel) },
		},
		settingsItem{
			title:       "Curve Target Speed Time Offset (s)",
			desc:        "An offset for the time before a target position to reach the target speed (map curve)",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "curve_target_speed_time_offset",
			value:       func() string { return fmt.Sprintf("%f s", p.CurveTargetSpeedTimeOffset) },
		},
		settingsItem{
			title:       "Speed Limit Increase Target Speed Time Offset (s)",
			desc:        "An offset for the time before a target position to reach the target speed (speed limit increasing)",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "speed_limit_increase_target_speed_time_offset",
			value:       func() string { return fmt.Sprintf("%f s", p.SpeedLimitIncreaseTargetSpeedTimeOffset) },
		},
		settingsItem{
			title:       "Speed Limit Decrease Target Speed Time Offset (s)",
			desc:        "An offset for the time before a target position to reach the target speed (speed limit decreasing)",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "speed_limit_decrease_target_speed_time_offset",
			value:       func() string { return fmt.Sprintf("%f s", p.SpeedLimitDecreaseTargetSpeedTimeOffset) },
		},
		settingsItem{
			title:       "Map Curve Target Lateral Acceleration (m/s^2)",
			desc:        "The maximum lateral acceleration used in the Map Curve Control speed calculations",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "map_curve_target_lat_a",
			value:       func() string { return fmt.Sprintf("%f m/s^2", p.MapCurveTargetLatA) },
		},
		settingsItem{
			title:       "Vision Curve Target Lateral Acceleration (m/s^2)",
			desc:        "The maximum lateral acceleration used in the Vision Curve Control speed calculations",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Float,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "vision_curve_target_lat_a",
			value:       func() string { return fmt.Sprintf("%f m/s^2", p.VisionCurveTargetLatA) },
		},
		settingsItem{
			title:       "Vision Minimum Target Velocity",
			desc:        "The minimum speed that Vision Curve Control will request to drive",
			MessageType: custom.MapdInputType_setJsonPathFloat,
			Type:        Speed,
			state:       unitsInput,
			jsonPath:    jsonPrefix + "vision_curve_min_target_v",
			value: func() string {
				val := p.VisionCurveMinTargetV
				mph := ms.MS_TO_MPH * val
				kph := ms.MS_TO_KPH * val
				return fmt.Sprintf("%f m/s, %f mph, %f kph", val, mph, kph)
			},
		},
		settingsItem{
			title:       "Slow Down For Next Speed Limit",
			desc:        "Determines if mapd will try to meet the upcoming speed limit before reaching it when the upcoming speed limit is lower than the current limit",
			MessageType: custom.MapdInputType_setJsonPathBool,
			Type:        Bool,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "slow_down_for_next_speed_limit",
			value:       func() string { return fmt.Sprintf("%t", p.SlowDownForNextSpeedLimit) },
		},
		settingsItem{
			title:       "Speed Up For Next Speed Limit",
			desc:        "Determines if mapd will try to meet the upcoming speed limit before reaching it when the upcoming speed limit is higher than the current limit",
			MessageType: custom.MapdInputType_setJsonPathBool,
			Type:        Bool,
			state:       settingsInput,
			jsonPath:    jsonPrefix + "speed_up_for_next_speed_limit",
			value:       func() string { return fmt.Sprintf("%t", p.SpeedUpForNextSpeedLimit) },
		},
		settingsItem{
			title: "Back to Personalities",
			desc:  "Return to personality selection",
			state: showPersonalitiesMenu,
			value: func() string { return "" },
		},
	}
}

var enableList = []list.Item{
	settingsItem{
		title: "Enable",
		value: func() string { return "" },
	},
	settingsItem{
		title: "Disable",
		value: func() string { return "" },
	},
}

var boolList = []list.Item{
	settingsItem{
		title: "Yes",
		value: func() string { return "" },
	},
	settingsItem{
		title: "No",
		value: func() string { return "" },
	},
}

var unitsList = []list.Item{
	settingsItem{
		title: "m/s",
		value: func() string { return "" },
	},
	settingsItem{
		title: "mph",
		value: func() string { return "" },
	},
	settingsItem{
		title: "kph",
		value: func() string { return "" },
	},
}

type SettingType int

const (
	String SettingType = iota
	Float
	Bool
	Speed
	Enable
	Options
)

type SpeedUnit int

const (
	Ms SpeedUnit = iota
	Mph
	Kph
)

type settingsState int

const (
	showSettingsMenu settingsState = iota
	settingsExit
	settingsInput
	unitsInput
	saveSettings
	defaultSettings
	recommendedSettings
	showPersonalitiesMenu
	showPersonalitySettings
	showSubscribersMenu
)

type settingsItem struct {
	title, desc string
	state       settingsState
	MessageType custom.MapdInputType
	Type        SettingType
	options     []list.Item
	value       func() string
	jsonPath    string
}

func (i settingsItem) Title() string {
	val := i.value()
	if val != "" {
		return i.title + " = " + val
	}
	return i.title
}
func (i settingsItem) Description() string { return i.desc }
func (i settingsItem) FilterValue() string { return i.title }

type settingsModel struct {
	list                list.Model
	state               settingsState
	textInput           textinput.Model
	selectedItem        settingsItem
	prompt              string
	speedUnit           SpeedUnit
	selectedPersonality string
	returnAfterInput    settingsState
}

func (m *settingsModel) restoreAfterInput() {
	switch m.returnAfterInput {
	case showPersonalitySettings:
		m.state = showPersonalitySettings
		m.list.SetItems(getPersonalitySettingsList(m.selectedPersonality))
		m.list.Title = strings.ToUpper(m.selectedPersonality[:1]) + m.selectedPersonality[1:] + " Personality Settings"
		m.list.ResetSelected()
	case showSubscribersMenu:
		m.state = showSubscribersMenu
		m.list.SetItems(subscribersList)
		m.list.Title = "Subscribers"
		m.list.ResetSelected()
	default:
		m.state = showSettingsMenu
		m.list.SetItems(settingsList)
		m.list.ResetSelected()
		m.list.Title = "Mapd Settings"
	}
}

func (m settingsModel) Update(msg tea.Msg, mm *uiModel) (settingsModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		isMenuState := m.state == showSettingsMenu || m.state == showPersonalitiesMenu || m.state == showPersonalitySettings || m.state == showSubscribersMenu
		if msg.Type == tea.KeyEnter && isMenuState && m.list.FilterState() != list.Filtering {
			it := m.list.SelectedItem().(settingsItem)
			m.selectedItem = it
			prevState := m.state
			m.state = it.state
			switch m.state {
			case settingsExit:
				m.state = showSettingsMenu
				mm.state = showMenu
			case settingsInput:
				m.returnAfterInput = prevState
				if m.selectedItem.Type == Enable {
					m.list.Title = m.selectedItem.Title()
					m.list.SetItems(enableList)
					m.list.ResetSelected()
				}
				if m.selectedItem.Type == Options {
					m.list.Title = m.selectedItem.Title()
					m.list.SetItems(m.selectedItem.options)
					m.list.ResetSelected()
				}
				if m.selectedItem.Type == Bool {
					m.list.Title = m.selectedItem.Title()
					m.list.SetItems(boolList)
					m.list.ResetSelected()
				}
				m.prompt = m.selectedItem.Title()
				m.textInput.Reset()
				m.textInput.Focus()
			case saveSettings:
				m.saveSettings(mm)
			case defaultSettings:
				msg, input := mm.pub.NewMessage(true)

				input.SetType(custom.MapdInputType_loadDefaultSettings)

				err := mm.pub.Send(msg)
				if err != nil {
					panic(err)
				}

				m.saveSettings(mm)
			case recommendedSettings:
				msg, input := mm.pub.NewMessage(true)

				input.SetType(custom.MapdInputType_loadRecommendedSettings)

				err := mm.pub.Send(msg)
				if err != nil {
					panic(err)
				}

				m.saveSettings(mm)
			case unitsInput:
				m.returnAfterInput = prevState
				m.list.SetItems(unitsList)
				m.list.Title = "Select Units"
				m.list.ResetSelected()
			case showPersonalitiesMenu:
				m.list.Title = "Personalities"
				m.list.SetItems(personalitiesList)
				m.list.ResetSelected()
			case showPersonalitySettings:
				personality := strings.ToLower(it.title)
				m.selectedPersonality = personality
				m.list.Title = it.title + " Personality Settings"
				m.list.SetItems(getPersonalitySettingsList(personality))
				m.list.ResetSelected()
			case showSubscribersMenu:
				m.list.Title = "Subscribers"
				m.list.SetItems(subscribersList)
				m.list.ResetSelected()
			case showSettingsMenu:
				m.list.Title = "Mapd Settings"
				m.list.SetItems(settingsList)
				m.list.ResetSelected()
			}
			return m, nil
		} else if msg.Type == tea.KeyEnter && m.state == unitsInput && m.list.FilterState() != list.Filtering {
			switch m.list.SelectedItem().(settingsItem).title {
			case "m/s":
				m.speedUnit = Ms
			case "mph":
				m.speedUnit = Mph
			case "kph":
				m.speedUnit = Kph
			}
			m.state = settingsInput
			m.prompt = m.selectedItem.title
			m.textInput.Reset()
			m.textInput.Focus()
		} else if msg.Type == tea.KeyEnter && m.state == settingsInput && m.list.FilterState() != list.Filtering {
			msg, input := mm.pub.NewMessage(true)

			input.SetType(m.selectedItem.MessageType)

			if m.selectedItem.jsonPath != "" {
				if err := input.SetJsonPath(m.selectedItem.jsonPath); err != nil {
					panic(err)
				}
			}

			result := m.textInput.Value()

			switch m.selectedItem.Type {
			case String:
				err := input.SetStr(result)
				if err != nil {
					panic(err)
				}
			case Bool:
				switch m.list.SelectedItem().(settingsItem).title {
				case "Yes":
					input.SetBool(true)
				case "No":
					input.SetBool(false)
				}
			case Float:
				val, err := strconv.ParseFloat(result, 32)
				if err != nil {
					panic(err)
				}
				input.SetFloat(float32(val))
			case Enable:
				switch m.list.SelectedItem().(settingsItem).title {
				case "Enable":
					input.SetBool(true)
				case "Disable":
					input.SetBool(false)
				}
			case Options:
				err := input.SetStr(m.list.SelectedItem().(settingsItem).title)
				if err != nil {
					panic(err)
				}
			case Speed:
				val, err := strconv.ParseFloat(result, 32)
				if err != nil {
					panic(err)
				}
				switch m.speedUnit {
				case Mph:
					val = val * ms.MPH_TO_MS
				case Kph:
					val = val * ms.KPH_TO_MS
				}
				input.SetFloat(float32(val))
			}
			err := mm.pub.Send(msg)
			if err != nil {
				panic(err)
			}
			m.restoreAfterInput()
			return m, nil
		}
	case tea.WindowSizeMsg:
		h, v := docStyle.GetFrameSize()
		m.list.SetSize(msg.Width-h, msg.Height-v)
		m.textInput.Width = msg.Width - h
		m.textInput.CharLimit = 256
	}

	var cmd tea.Cmd
	switch m.state {
	case settingsInput:
		switch m.selectedItem.Type {
		case Enable:
			m.list, cmd = m.list.Update(msg)
		case Bool:
			m.list, cmd = m.list.Update(msg)
		case Options:
			m.list, cmd = m.list.Update(msg)
		default:
			m.textInput, cmd = m.textInput.Update(msg)
		}
	default:
		m.list, cmd = m.list.Update(msg)
	}
	return m, cmd
}

func (m *settingsModel) saveSettings(mm *uiModel) {
	m.state = showSettingsMenu
	mm.state = showMenu

	msg, input := mm.pub.NewMessage(true)

	input.SetType(custom.MapdInputType_saveSettings)

	err := mm.pub.Send(msg)
	if err != nil {
		panic(err)
	}
}

func (m settingsModel) View() string {
	switch m.state {
	case settingsInput:
		switch m.selectedItem.Type {
		case Enable:
			return docStyle.Render(m.list.View())
		case Bool:
			return docStyle.Render(m.list.View())
		case Options:
			return docStyle.Render(m.list.View())
		default:
			return docStyle.Render(fmt.Sprintf(
				"%s\n\n%s\n\n%s",
				m.prompt,
				m.textInput.View(),
				"(esc to quit)",
			) + "\n")
		}
	default:
		return docStyle.Render(m.list.View())
	}
}

func getSettingsModel() settingsModel {
	listDelegate := list.NewDefaultDelegate()
	m := settingsModel{list: list.New(settingsList, listDelegate, 0, 0), textInput: textinput.New()}
	m.list.Title = "Mapd Settings"
	return m
}
