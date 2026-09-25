package main

import (
	"encoding/json"
	"log/slog"
	"time"

	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cereal/custom"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
	"pfeifer.dev/mapd/utils"
)

type ExtendedState struct {
	DownloadProgress ms.DownloadProgress
	Pub              cereal.Publisher[custom.MapdExtendedOut]
	LoopRate         utils.LoopRateTracker
	lastSend         time.Time
	state            *State
}

func (s *ExtendedState) Send() error {
	s.state.ExpireGpsEvidence()
	if time.Since(s.lastSend) > 1*time.Second {
		s.lastSend = time.Now()
		msg, out := s.Pub.NewMessage(true)
		s.setDownloadProgress(out)
		s.setSettings(out)
		s.setPath(out)
		s.setPosition(out)
		s.setLoopRate(out)
		s.Pub.Publish(msg)
		return nil
	}
	return nil
}

func (s *ExtendedState) setPosition(out custom.MapdExtendedOut) {
	if s.state.RoadStatus == custom.MapdOut_SampleStatus_noGps {
		return
	}
	position, err := out.NewPosition()
	if err == nil {
		position.SetLatitude(s.state.Position.Lat())
		position.SetLongitude(s.state.Position.Lon())
		out.SetPosition(position)
	}
}

func (s *ExtendedState) setPath(out custom.MapdExtendedOut) {
	if !s.state.RoadMatched() {
		_, _ = out.NewPath(0)
		return
	}
	nodes := s.state.CurrentWay.Way.Nodes.Slice()
	num_points := len(nodes)
	all_nodes := [][]m.Position{nodes}
	all_nodes_direction := []bool{s.state.CurrentWay.OnWay.IsForward}
	for _, nextWay := range s.state.NextWays {
		nwNodes := nextWay.Way.Nodes.Slice()
		if len(nwNodes) > 0 {
			num_points += len(nwNodes) - 1
		}
		all_nodes = append(all_nodes, nwNodes)
		all_nodes_direction = append(all_nodes_direction, nextWay.IsForward)
	}

	path, err := out.NewPath(int32(num_points))
	if err != nil {
		slog.Warn("failed to create path in extended state")
		return
	}

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
		point := path.At(i)
		point.SetLatitude(node.Lat())
		point.SetLongitude(node.Lon())
		nodes_idx += 1
		if nodes_idx == len(all_nodes[all_nodes_idx]) || (nodes_idx == len(all_nodes[all_nodes_idx])-1 && all_nodes_idx > 0) {
			all_nodes_idx += 1
			nodes_idx = 0
		}
	}
	point_idx := 0
	for _, curvature := range s.state.Curvatures {
		for ; point_idx < path.Len(); point_idx++ {
			point := path.At(point_idx)
			pos := m.NewPosition(point.Latitude(), point.Longitude())
			if curvature.Pos.Equals(pos) {
				point.SetCurvature(float32(curvature.Curvature))
				point_idx++
				break
			}
		}
	}
	point_idx = 0
	for _, velocity := range s.state.TargetVelocities {
		for ; point_idx < path.Len(); point_idx++ {
			point := path.At(point_idx)
			pos := m.NewPosition(point.Latitude(), point.Longitude())
			if velocity.Pos.Equals(pos) {
				point.SetTargetVelocity(float32(velocity.Velocity))
				point_idx++
				break
			}
		}
	}
}

func (s *ExtendedState) setLoopRate(out custom.MapdExtendedOut) {
	out.SetLoopRateAverage(float32(s.LoopRate.AverageRate()))
	out.SetLoopRateMin(float32(s.LoopRate.MinRate()))
}

func (s *ExtendedState) setSettings(out custom.MapdExtendedOut) {
	b, err := json.Marshal(ms.Settings)
	if err != nil {
		slog.Warn("failed to marshal settings for extended state")
		return
	}
	if err := out.SetSettings(string(b)); err != nil {
		slog.Warn("failed to set settings in extended state")
	}
}

func (s *ExtendedState) setDownloadProgress(out custom.MapdExtendedOut) {
	p, err := out.NewDownloadProgress()
	if err != nil {
		panic(err)
	}
	p.SetActive(s.DownloadProgress.Active)
	p.SetCancelled(s.DownloadProgress.Canceled)
	p.SetTotalFiles(uint32(s.DownloadProgress.TotalFiles))
	p.SetDownloadedFiles(uint32(s.DownloadProgress.DownloadedFiles))
	l, err := p.NewLocations(int32(len(s.DownloadProgress.LocationsToDownload)))
	if err != nil {
		panic(err)
	}
	for i, location := range s.DownloadProgress.LocationsToDownload {
		err := l.Set(i, location)
		if err != nil {
			panic(err)
		}
	}
	ld, err := p.NewLocationDetails(int32(len(s.DownloadProgress.LocationDetails)))
	if err != nil {
		panic(err)
	}
	idx := 0
	for location, locationDetails := range s.DownloadProgress.LocationDetails {
		d := ld.At(idx)
		err := d.SetLocation(location)
		if err != nil {
			panic(err)
		}
		d.SetDownloadedFiles(uint32(locationDetails.DownloadedFiles))
		d.SetTotalFiles(uint32(locationDetails.TotalFiles))
		idx++
	}
}
