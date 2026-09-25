package main

import (
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
)

func UpdateCurveSpeed(s *State) {
	distances := make([]float32, len(s.TargetVelocities))
	match_idx := -1
	for i, tv := range s.TargetVelocities {
		d, found, _ := s.CurrentWay.Way.DistanceToNode(s.Position, s.CurrentWay.OnWay.IsForward, tv.Pos)
		if !found {
			distance := float32(0.0)
			for _, nextWay := range s.NextWays {
				distance, found, _ = nextWay.Way.DistanceToNode(nextWay.StartPosition, nextWay.IsForward, tv.Pos)
				d += distance
				if found {
					break
				}
			}
			if !found {
				d = s.CurrentWay.OnWay.Distance.LinePosition.Pos.DistanceTo(tv.Pos)
			}
		}

		distances[i] = d

		// find index of the most recent node we have driven past based on which node was used to calculate if we are on the way
		if tv.Pos.Equals(s.CurrentWay.Distance.LineStart) && match_idx == -1 {
			match_idx = i + 1
		}
		if tv.Pos.Equals(s.CurrentWay.Distance.LineEnd) && match_idx == -1 {
			match_idx = i + 1
		}
	}
	if match_idx == -1 {
		match_idx = 0
	}
	forwardSize := len(s.TargetVelocities) - match_idx
	forwardPoints := make([]*Velocity, forwardSize)
	forwardDistances := make([]float32, forwardSize)

	for i := range forwardSize {
		forwardPoints[i] = &s.TargetVelocities[i+match_idx]
		forwardDistances[i] = distances[i+match_idx] - s.DistanceSinceLastPosition
		if forwardDistances[i] <= 0 {
			forwardDistances[i] = distances[i+match_idx]
		}
	}

	minValidV := float32(1000)
	for i, d := range forwardDistances {
		tv := forwardPoints[i]
		if tv.Velocity > float64(s.Car.VEgo)+ms.CURVE_CALC_OFFSET {
			continue
		}

		max_d := tv.TriggerDistance
		if max_d == 0 {
			personality := ms.Settings.CurrentPersonality()
			max_d = m.CalculateJerkLimitedDistanceSimple(s.Car.VEgo, s.Car.AEgo, float32(tv.Velocity), personality.TargetSpeedAccel, personality.TargetSpeedJerk)
			max_d += personality.CurveTargetSpeedTimeOffset * float32(tv.Velocity)
		}

		if float32(d) < max_d {
			if tv.TriggerDistance != max_d {
				tv.TriggerDistance = max_d + 15
			}
			if float32(tv.Velocity) < minValidV {
				minValidV = float32(tv.Velocity)
			}
		}
	}
	if minValidV == float32(1000) {
		s.MapCurveSpeed = 0
	} else {
		s.MapCurveSpeed = minValidV
	}
}
