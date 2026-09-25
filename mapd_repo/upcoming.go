package main

import (
	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
)

func NewUpcoming[T any](maLength int, defaultValue T, checkWay CheckWay[T]) Upcoming[T] {
	u := Upcoming[T]{
		CheckWay:     checkWay,
		DefaultValue: defaultValue,
		Value:        defaultValue,
	}
	return u
}

type CheckWay[T any] func(*State, *Upcoming[T], maps.NextWayResult) (valid bool, val T)

type Upcoming[T any] struct {
	CheckWay        CheckWay[T]
	DefaultValue    T
	Value           T
	Position        m.Position
	Distance        float32
	RawDistance     float32
	TriggerDistance float32
}

func (u *Upcoming[T]) Reset() {
	u.Distance = 0
	u.RawDistance = 0
	u.TriggerDistance = 0
	u.Value = u.DefaultValue
	u.Position = m.Position{}
}

func (u *Upcoming[T]) Update(state *State) {
	if len(state.NextWays) == 0 {
		u.Reset()
		return
	}

	cumulativeDistance := float32(0.0)

	if state.CurrentWay.Way.Nodes.Len() > 0 {
		distToEnd, err := state.CurrentWay.Way.DistanceToEnd(state.Position, state.CurrentWay.OnWay.IsForward)
		if err == nil {
			cumulativeDistance = distToEnd
		}
	}
	for _, nextWay := range state.NextWays {
		valid, val := u.CheckWay(state, u, nextWay)
		if valid {
			cumulativeDistance -= state.DistanceSinceLastPosition
			if u.Position.Equals(nextWay.StartPosition) {
				u.Distance = min(u.Distance, cumulativeDistance)
				if m.Abs(u.Distance-cumulativeDistance) > 100 {
					u.Distance = cumulativeDistance
				}
			} else {
				u.Distance = cumulativeDistance
				u.TriggerDistance = 0
			}
			u.Position = nextWay.StartPosition
			u.RawDistance = cumulativeDistance
			u.Value = val
			return
		}
		cumulativeDistance += nextWay.Way.Distance()
	}

	// No upcoming way found, reset state
	u.Reset()
}
