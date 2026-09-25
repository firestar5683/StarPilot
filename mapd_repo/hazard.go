package main

import (
	"pfeifer.dev/mapd/maps"
)

func checkWayForHazardChange(state *State, parent *Upcoming[string], way maps.NextWayResult) (valid bool, val string) {
	nextHazard := way.Way.Hazard()

	if nextHazard != state.CurrentWay.Way.Hazard() && nextHazard != "" {
		return true, nextHazard
	}

	return false, parent.DefaultValue
}
