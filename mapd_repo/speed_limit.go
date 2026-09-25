package main

import (
	"strconv"
	"strings"
	"time"

	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
	"pfeifer.dev/mapd/utils"
)

type SpeedLimitState struct {
	Limit                utils.Float32Tracker
	Suggestion           utils.Float32Tracker
	SetSpeedWhenAccepted float32
	OverrideSpeed        float32
	AcceptedLimit        float32
	NextLimit            Upcoming[float32]
}

func (s *SpeedLimitState) Init() {
	s.Limit.AllowNullLastValue = false
	s.Suggestion.AllowNullLastValue = true

	s.NextLimit = NewUpcoming(10, 0, checkWayForSpeedLimitChange)
}

func (s *SpeedLimitState) Update(currentWay CurrentWay, car CarState) {
	if ms.Settings.SpeedLimitSettings.PressGasToOverrideSpeedLimit && car.GasPressed && car.VEgo > s.AcceptedLimit {
		s.OverrideSpeed = car.VEgo
	}
	if s.OverrideSpeed < s.AcceptedLimit {
		s.OverrideSpeed = 0
	}
	if car.SetSpeedChanging {
		s.OverrideSpeed = 0
	}
	s.UpdateLimitAcceptedState(car)
	s.UpdateAcceptedLimitValue(currentWay, car)
}

func (s *SpeedLimitState) UpdateLimitAcceptedState(car CarState) {
	timeout := ms.Settings.SpeedLimitSettings.AcceptSpeedLimitTimeout
	if timeout > 0 && time.Since(s.Limit.UpdatedTime) > time.Duration(timeout)*time.Second {
		return
	}
	if ms.Settings.SpeedLimitSettings.PressGasToAcceptSpeedLimit && car.GasPressed {
		ms.Settings.AcceptSpeedLimit()
	}
	if ms.Settings.SpeedLimitSettings.AdjustSetSpeedToAcceptSpeedLimit && car.SetSpeed.UpdatedTime.After(s.Limit.UpdatedTime) {
		if ms.Settings.SpeedLimitAccepted() && s.SetSpeedWhenAccepted != car.SetSpeed.Value {
			ms.Settings.ResetSpeedLimitAccepted()
		}
		if s.SetSpeedWhenAccepted == 0 {
			s.SetSpeedWhenAccepted = car.SetSpeed.Value
			ms.Settings.AcceptSpeedLimit()
		}
	}
}

func (s *SpeedLimitState) UpdateAcceptedLimitValue(currentWay CurrentWay, car CarState) {
	suggestedSpeedUpdated := s.Suggestion.Update(s.SuggestNewSpeedLimit(currentWay, car))
	if suggestedSpeedUpdated {
		ms.Settings.ResetSpeedLimitAccepted()
		s.SetSpeedWhenAccepted = 0
	}
	if ms.Settings.SpeedLimitAccepted() {
		if s.AcceptedLimit != s.Suggestion.Value {
			s.OverrideSpeed = 0
		}
		s.AcceptedLimit = s.Suggestion.Value
	}
}

func (s *SpeedLimitState) SpeedLimitFinalSuggestion(enableSpeedActive bool, setSpeedChanging bool, vEgo float32) float32 {
	slSuggestedSpeed := s.AcceptedLimit
	if s.OverrideSpeed > 0 && s.OverrideSpeed > slSuggestedSpeed {
		slSuggestedSpeed = s.OverrideSpeed
	}
	if !ms.Settings.SpeedLimitUseEnableSpeed || enableSpeedActive {
		return slSuggestedSpeed
	} else if setSpeedChanging && ms.Settings.SpeedLimitSettings.HoldSpeedLimitWhileChangingSetSpeed && vEgo-1 < s.AcceptedLimit {
		return slSuggestedSpeed
	}
	return 0
}

func (s *SpeedLimitState) SuggestNewSpeedLimit(currentWay CurrentWay, car CarState) float32 {
	slSuggestedSpeed := ms.Settings.PrioritySpeedLimit(float32(currentWay.EffectiveMaxSpeed()))
	if slSuggestedSpeed == 0 && ms.Settings.SpeedLimitSettings.HoldLastSeenSpeedLimit {
		slSuggestedSpeed = float32(s.Limit.LastValue)
	}
	if slSuggestedSpeed > 0 {
		slSuggestedSpeed += ms.Settings.SpeedLimitSettings.SpeedLimitOffset
	}
	if s.NextLimit.Value > 0 {
		offsetNextSpeedLimit := s.NextLimit.Value + ms.Settings.SpeedLimitSettings.SpeedLimitOffset
		s.Limit.Update(ms.Settings.PrioritySpeedLimit(float32(currentWay.EffectiveMaxSpeed())))
		nextIsLower := s.Limit.Value > s.NextLimit.Value
		personality := ms.Settings.CurrentPersonality()
		distanceToReachSpeed := m.CalculateJerkLimitedDistanceSimple(car.VEgo, car.AEgo, offsetNextSpeedLimit, personality.TargetSpeedAccel, personality.TargetSpeedJerk)
		if nextIsLower {
			distanceToReachSpeed += personality.SpeedLimitDecreaseTargetSpeedTimeOffset * (s.NextLimit.Value + ms.Settings.SpeedLimitSettings.SpeedLimitOffset)
		} else {
			distanceToReachSpeed += personality.SpeedLimitIncreaseTargetSpeedTimeOffset * (s.NextLimit.Value + ms.Settings.SpeedLimitSettings.SpeedLimitOffset)
		}
		if s.NextLimit.TriggerDistance > distanceToReachSpeed {
			distanceToReachSpeed = s.NextLimit.TriggerDistance
		}
		if distanceToReachSpeed > s.NextLimit.TriggerDistance {
			s.NextLimit.TriggerDistance = distanceToReachSpeed + 10
		}
		if !nextIsLower && personality.SpeedUpForNextSpeedLimit && s.NextLimit.Distance < distanceToReachSpeed {
			slSuggestedSpeed = float32(offsetNextSpeedLimit)
		} else if nextIsLower && personality.SlowDownForNextSpeedLimit && s.NextLimit.Distance < distanceToReachSpeed {
			slSuggestedSpeed = float32(offsetNextSpeedLimit)
		}
	}
	return slSuggestedSpeed
}

func ParseMaxSpeed(maxspeed string) float64 {
	splitSpeed := strings.Split(maxspeed, " ")
	if len(splitSpeed) == 0 {
		return 0
	}

	numeric, err := strconv.ParseUint(splitSpeed[0], 10, 64)
	if err != nil {
		return 0
	}

	if len(splitSpeed) == 1 {
		return ms.KPH_TO_MS * float64(numeric)
	}

	if splitSpeed[1] == "kph" || splitSpeed[1] == "km/h" || splitSpeed[1] == "kmh" {
		return ms.KPH_TO_MS * float64(numeric)
	} else if splitSpeed[1] == "mph" {
		return ms.MPH_TO_MS * float64(numeric)
	} else if splitSpeed[1] == "knots" {
		return ms.KNOTS_TO_MS * float64(numeric)
	}

	return 0
}

func checkWayForSpeedLimitChange(state *State, parent *Upcoming[float32], way maps.NextWayResult) (valid bool, val float32) {
	nextMaxSpeed := way.Way.MaxSpeed()
	if way.IsForward && way.Way.MaxSpeedForward() > 0 {
		nextMaxSpeed = way.Way.MaxSpeedForward()
	} else if !way.IsForward && way.Way.MaxSpeedBackward() > 0 {
		nextMaxSpeed = way.Way.MaxSpeedBackward()
	}
	if ms.Settings.ConditionalSpeedLimitControlEnabled {
		rules := way.Way.ConditionalSpeedRules(way.IsForward)
		if conditional := maps.ConditionalSpeedAt(rules, time.Now()); conditional > 0 {
			nextMaxSpeed = conditional
		}
	}

	if nextMaxSpeed != state.CurrentWay.EffectiveMaxSpeed() && nextMaxSpeed > 0 {
		return true, float32(nextMaxSpeed)
	}

	return false, parent.DefaultValue
}

func checkWayForAdvisorySpeedChange(state *State, parent *Upcoming[float32], way maps.NextWayResult) (valid bool, val float32) {
	nextAdvisorySpeed := way.Way.AdvisorySpeed()

	if nextAdvisorySpeed != state.CurrentWay.Way.AdvisorySpeed() && nextAdvisorySpeed > 0 {
		return true, float32(nextAdvisorySpeed)
	}

	return false, parent.DefaultValue
}
