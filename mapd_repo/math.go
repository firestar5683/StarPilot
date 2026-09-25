package main

import (
	"fmt"
	"math"

	"github.com/pkg/errors"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
)

func GetStateCurvatures(state *State) ([]m.Curvature, error) {
	nodes := state.CurrentWay.Way.Nodes.Slice()
	num_points := len(nodes)
	all_nodes := [][]m.Position{nodes}
	all_nodes_direction := []bool{state.CurrentWay.OnWay.IsForward}
	all_nodes_is_merge_or_split := []bool{false}
	lastWay := state.CurrentWay.Way
	for _, nextWay := range state.NextWays {
		nwNodes := nextWay.Way.Nodes.Slice()
		if len(nwNodes) > 0 {
			num_points += len(nwNodes) - 1
		}
		all_nodes = append(all_nodes, nwNodes)
		all_nodes_direction = append(all_nodes_direction, nextWay.IsForward)
		all_nodes_is_merge_or_split = append(all_nodes_is_merge_or_split, lastWay.Lanes() < nextWay.Way.Lanes() || (lastWay.Lanes() > nextWay.Way.Lanes() && !lastWay.OneWay() && nextWay.Way.OneWay()))
		lastWay = nextWay.Way
	}

	positions := make([]m.Position, num_points)

	merge_or_split_nodes := []int{}
	all_nodes_idx := 0
	nodes_idx := 0
	for i := 0; i < num_points; i++ {
		var index int
		forward := all_nodes_direction[all_nodes_idx]
		if forward {
			index = nodes_idx
			if all_nodes_idx > 0 {
				index += 1
			}
		} else {
			index = len(all_nodes[all_nodes_idx]) - nodes_idx - 1
			if all_nodes_idx > 0 {
				index -= 1
			}
		}
		node := all_nodes[all_nodes_idx][index]
		positions[i] = node

		nodes_idx += 1
		if nodes_idx == len(all_nodes[all_nodes_idx]) || (nodes_idx == len(all_nodes[all_nodes_idx])-1 && all_nodes_idx > 0) {
			all_nodes_idx += 1
			nodes_idx = 0
			if all_nodes_idx < len(all_nodes_is_merge_or_split) && all_nodes_is_merge_or_split[all_nodes_idx] {
				merge_or_split_nodes = append(merge_or_split_nodes, i)
			}
		}
	}

	curvatures, err := GetCurvatures(positions)
	if err != nil {
		return []m.Curvature{}, errors.Wrap(err, "could not get curvatures from points")
	}

	// set the merge nodes to be straight to help balance out issues with map representation
	for _, merge_or_split_node := range merge_or_split_nodes {
		if merge_or_split_node >= 2 {
			curvatures[merge_or_split_node-2].Curvature = 0.0015
			curvatures[merge_or_split_node-1].Curvature = 0.0015
		}
		// also include nodes within 15 meters
		for i := merge_or_split_node - 3; i >= 0; i-- {

			if positions[merge_or_split_node].DistanceTo(positions[i]) > 15 {
				break
			}
			curvatures[i].Curvature = 0.0015
		}
		// also include forward nodes within 15 meters
		for i := merge_or_split_node; i < len(curvatures); i++ {
			if positions[merge_or_split_node].DistanceTo(positions[i]) > 15 {
				break
			}
			curvatures[i].Curvature = 0.0015
		}
	}

	average_curvatures, err := GetAverageCurvatures(curvatures)
	if err != nil {
		return []m.Curvature{}, errors.Wrap(err, "could not get average curvatures from curvatures")
	}
	return average_curvatures, nil
}

type Velocity struct {
	Pos             m.Position
	Velocity        float64
	TriggerDistance float32
}

func GetTargetVelocities(curvatures []m.Curvature, previousTargets []Velocity) (velocities []Velocity) {
	velocities = make([]Velocity, len(curvatures))
	for i, curv := range curvatures {
		if curv.Curvature == 0 {
			continue
		}
		velocities[i].Velocity = math.Pow(float64(ms.Settings.CurrentPersonality().MapCurveTargetLatA)/curv.Curvature, 1.0/2)
		velocities[i].Pos = curv.Pos
		for _, t := range previousTargets {
			if velocities[i].Pos.Equals(t.Pos) {
				velocities[i].TriggerDistance = t.TriggerDistance
			}
		}
	}
	return velocities
}

func GetAverageCurvatures(curvatures []m.Curvature) (average_curvatures []m.Curvature, err error) {
	if len(curvatures) < 3 {
		return []m.Curvature{}, errors.New("not enough curvatures to average")
	}

	average_curvatures = make([]m.Curvature, len(curvatures)-2)

	for i := 0; i < len(curvatures)-2; i++ {
		a := curvatures[i].Curvature
		b := curvatures[i+1].Curvature
		c := curvatures[i+2].Curvature
		al := curvatures[i].ArcLength
		bl := curvatures[i+1].ArcLength
		cl := curvatures[i+2].ArcLength

		if al+bl+cl == 0 {
			average_curvatures[i] = curvatures[i+2]
			continue
		}

		avg := m.Curvature{Pos: curvatures[i+1].Pos}
		avg.Curvature = (a*al + b*bl + c*cl) / (al + bl + cl)
		avg.ArcLength = (curvatures[i].ArcLength + curvatures[i+1].ArcLength + curvatures[i+2].ArcLength) / 3
		avg.Angle = (curvatures[i].Angle + curvatures[i+1].Angle + curvatures[i+2].Angle) / 3
		average_curvatures[i] = avg
	}

	return average_curvatures, nil
}

func GetCurvatures(positions []m.Position) (curvatures []m.Curvature, err error) {
	if len(positions) < 3 {
		return []m.Curvature{}, errors.New(fmt.Sprintf("not enough points to calculate curvatures. len(points): %d", len(positions)))
	}
	curvatures = make([]m.Curvature, len(positions)-2)

	for i := 0; i < len(positions)-2; i++ {
		curvature := m.CalculateCurvature(positions[i], positions[i+1], positions[i+2])

		curvatures[i] = curvature
	}

	return curvatures, nil
}
