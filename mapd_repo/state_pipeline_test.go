package main

import (
	"errors"
	"math"
	"os"
	"path/filepath"
	"testing"
	"time"

	"capnproto.org/go/capnp/v3"
	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/cereal/offline"
	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
)

func diskTileBytes(t *testing.T, speed float64) []byte {
	t.Helper()
	msg, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	tile, err := offline.NewRootOffline(seg)
	if err != nil {
		t.Fatal(err)
	}
	tile.SetMinLat(35)
	tile.SetMaxLat(35.25)
	tile.SetMinLon(-98)
	tile.SetMaxLon(-97.75)
	ways, err := tile.NewWays(1)
	if err != nil {
		t.Fatal(err)
	}
	w := ways.At(0)
	w.SetId(42)
	w.SetMaxSpeed(speed)
	w.SetMinLat(35.1)
	w.SetMaxLat(35.2)
	w.SetMinLon(-97.9)
	w.SetMaxLon(-97.9)
	nodes, err := w.NewNodes(2)
	if err != nil {
		t.Fatal(err)
	}
	nodes.At(0).SetLatitude(35.1)
	nodes.At(0).SetLongitude(-97.9)
	nodes.At(1).SetLatitude(35.2)
	nodes.At(1).SetLongitude(-97.9)
	data, err := msg.MarshalPacked()
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestDiskTileReplacementClearsProducerEvidence(t *testing.T) {
	old := maps.DEFAULT_SETTINGS.OutputDirectory
	defer func() { maps.DEFAULT_SETTINGS.OutputDirectory = old }()
	maps.DEFAULT_SETTINGS.OutputDirectory = t.TempDir()
	area := maps.Area{Box: m.Box{MinPos: m.NewPosition(35, -98), MaxPos: m.NewPosition(35.25, -97.75)}}
	path := maps.GenerateBoundsFileName(area, maps.DEFAULT_SETTINGS)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	write := func(name string, speed float64) {
		t.Helper()
		if err := os.WriteFile(name, diskTileBytes(t, speed), 0644); err != nil {
			t.Fatal(err)
		}
	}
	write(path, 13)
	s := State{}
	s.Init()
	boot := uint64(10_100_000_000)
	s.bootNow = func() uint64 { return boot }
	first := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
	s.ProcessGps(first, true, maps.FindWaysAroundPosition, time.Unix(0, 0))
	event, out := decodedOutput(t, &s)
	if !event.Valid() || out.SpeedLimit() != 13 {
		t.Fatalf("initial limit: valid=%v limit=%f", event.Valid(), out.SpeedLimit())
	}
	// Replacement after processing must be caught at the final output boundary.
	stage := path + ".new"
	write(stage, 8)
	if err := os.Rename(stage, path); err != nil {
		t.Fatal(err)
	}
	event, out = decodedOutput(t, &s)
	if event.Valid() || out.SpeedLimit() != 0 || out.WayId() != 0 || out.RoadStatus() != custom.MapdOut_SampleStatus_noCoverage {
		t.Fatalf("stale post-replacement output: valid=%v status=%v limit=%f", event.Valid(), out.RoadStatus(), out.SpeedLimit())
	}
	// A same-fix loop may recover only through a fresh validated load.
	second := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, false, false)
	s.ProcessGps(second, true, maps.FindWaysAroundPosition, time.Unix(0, 1))
	event, out = decodedOutput(t, &s)
	if !event.Valid() || out.SpeedLimit() != 8 {
		t.Fatalf("replacement recovery: valid=%v limit=%f", event.Valid(), out.SpeedLimit())
	}
	// An invalid in-place rewrite must immediately neutralize accepted evidence.
	if err := os.WriteFile(path, []byte{0xff}, 0644); err != nil {
		t.Fatal(err)
	}
	s.ProcessGps(second, true, maps.FindWaysAroundPosition, time.Unix(0, 2))
	event, out = decodedOutput(t, &s)
	if event.Valid() || out.SpeedLimit() != 0 || out.WayId() != 0 {
		t.Fatalf("malformed replacement retained limit: valid=%v limit=%f", event.Valid(), out.SpeedLimit())
	}
}

func syntheticTile(t *testing.T, maxSpeed float64, withWay bool) maps.Offline {
	t.Helper()
	msg, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	tile, err := offline.NewRootOffline(seg)
	if err != nil {
		t.Fatal(err)
	}
	tile.SetMinLat(35)
	tile.SetMaxLat(35.25)
	tile.SetMinLon(-98)
	tile.SetMaxLon(-97.75)
	count := int32(0)
	if withWay {
		count = 1
	}
	ways, err := tile.NewWays(count)
	if err != nil {
		t.Fatal(err)
	}
	if withWay {
		way := ways.At(0)
		way.SetId(42)
		way.SetMaxSpeed(maxSpeed)
		way.SetMinLat(35.1)
		way.SetMaxLat(35.2)
		way.SetMinLon(-97.901)
		way.SetMaxLon(-97.899)
		if err := way.SetName("Synthetic road"); err != nil {
			t.Fatal(err)
		}
		nodes, err := way.NewNodes(2)
		if err != nil {
			t.Fatal(err)
		}
		nodes.At(0).SetLatitude(35.1)
		nodes.At(0).SetLongitude(-97.9)
		nodes.At(1).SetLatitude(35.2)
		nodes.At(1).SetLongitude(-97.9)
	}
	data, err := msg.MarshalPacked()
	if err != nil {
		t.Fatal(err)
	}
	parsed := maps.ReadOffline(data)
	if !parsed.Loaded {
		t.Fatal("synthetic tile rejected")
	}
	return parsed
}

func syntheticSample(t *testing.T, source cereal.GpsSource, mono, generation uint64, changed, newFix bool) cereal.GpsSample {
	t.Helper()
	_, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	location, err := log.NewRootGpsLocationData(seg)
	if err != nil {
		t.Fatal(err)
	}
	location.SetHasFix(true)
	location.SetLatitude(35.15)
	location.SetLongitude(-97.9)
	location.SetBearingDeg(0)
	location.SetHorizontalAccuracy(5)
	return cereal.GpsSample{Location: location, Source: source, FixMonoTime: mono, SourceGeneration: generation, SourceChanged: changed, NewFix: newFix}
}

func decodedOutput(t *testing.T, s *State) (log.Event, custom.MapdOut) {
	t.Helper()
	msg, err := s.BuildMessage()
	if err != nil {
		t.Fatal(err)
	}
	data, err := msg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := capnp.Unmarshal(data)
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.ReadRootEvent(decoded)
	if err != nil {
		t.Fatal(err)
	}
	out, err := event.MapdOut()
	if err != nil {
		t.Fatal(err)
	}
	return event, out
}

func TestSyntheticRoadSampleWireAndSameFixReuse(t *testing.T) {
	s := State{}
	s.Init()
	tile := syntheticTile(t, 13.4112, true)
	loads := 0
	loader := func(m.Position) (maps.Offline, error) { loads++; return tile, nil }
	fix := uint64(10_000_000_000)
	boot := fix + 100_000_000
	s.bootNow = func() uint64 { return boot }
	sample := syntheticSample(t, cereal.GpsSourceExternal, fix, 1, true, true)
	now := time.Unix(0, 0)
	s.ProcessGps(sample, true, loader, now)
	event, out := decodedOutput(t, &s)
	if !event.Valid() || out.SampleVersion() != 2 || out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit || out.GpsSource() != custom.MapdOut_GpsSource_external || out.GpsMonoTime() != fix || out.ComputedMonoTime() == 0 || out.SourceGeneration() != 1 || out.ProducerSession() == 0 || out.WayId() != 42 || math.Abs(float64(out.SpeedLimit()-13.4112)) > 0.001 {
		t.Fatalf("qualified synthetic road: eventValid=%v status=%v source=%v gps=%d computed=%d generation=%d session=%d way=%d limit=%f", event.Valid(), out.RoadStatus(), out.GpsSource(), out.GpsMonoTime(), out.ComputedMonoTime(), out.SourceGeneration(), out.ProducerSession(), out.WayId(), out.SpeedLimit())
	}
	s.DistanceSinceLastPosition = 7
	sample.NewFix = false
	sample.SourceChanged = false
	s.ProcessGps(sample, true, loader, now.Add(50*time.Millisecond))
	_, out = decodedOutput(t, &s)
	if s.DistanceSinceLastPosition != 7 || out.GpsMonoTime() != fix || loads != 1 {
		t.Fatalf("same fix reuse changed distance/time or reloaded tile: distance=%f gps=%d loads=%d", s.DistanceSinceLastPosition, out.GpsMonoTime(), loads)
	}
}

func TestSyntheticMissingLimitAndInvalidation(t *testing.T) {
	s := State{}
	s.Init()
	boot := uint64(10_001)
	s.bootNow = func() uint64 { return boot }
	sample := syntheticSample(t, cereal.GpsSourceInternal, 10_000, 1, true, true)
	now := time.Unix(0, 0)
	noLimit := syntheticTile(t, 0, true)
	s.ProcessGps(sample, true, func(m.Position) (maps.Offline, error) { return noLimit, nil }, now)
	event, out := decodedOutput(t, &s)
	if !event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_matchedNoLimit || out.SpeedLimit() != 0 || out.SpeedLimitSuggestedSpeed() != 0 || out.WayId() != 42 {
		t.Fatalf("unknown posted limit must keep geography but no numeric authority: %+v", out)
	}
	s.DistanceSinceLastPosition = 9
	s.MapCurveSpeed = 11
	s.NextHazard.Value = "old hazard"
	s.SpeedLimit.AcceptedLimit = 12
	lost := cereal.GpsSample{Source: cereal.GpsSourceNone, SourceGeneration: 2, SourceChanged: true}
	s.ProcessGps(lost, false, nil, now.Add(time.Second))
	event, out = decodedOutput(t, &s)
	if event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_noGps || out.SpeedLimit() != 0 || out.WayId() != 0 || out.GpsMonoTime() != 0 || out.SourceGeneration() != 2 || s.DistanceSinceLastPosition != 0 || s.MapCurveSpeed != 0 || s.NextHazard.Value != "" || s.SpeedLimit.AcceptedLimit != 0 || s.Data.Loaded {
		t.Fatalf("lost source retained road evidence: status=%v speed=%f", out.RoadStatus(), out.SpeedLimit())
	}
}

func TestSourceSwitchClearsStickyRoadEvidenceBeforeNewMatch(t *testing.T) {
	s := State{}
	s.Init()
	boot := uint64(10_001)
	s.bootNow = func() uint64 { return boot }
	now := time.Unix(0, 0)
	first := syntheticSample(t, cereal.GpsSourceExternal, 10_000, 1, true, true)
	oldTile := syntheticTile(t, 13, true)
	s.ProcessGps(first, true, func(m.Position) (maps.Offline, error) { return oldTile, nil }, now)
	if !s.RoadMatched() {
		t.Fatal("initial road did not match")
	}
	s.SpeedLimit.AcceptedLimit = 13
	s.SpeedLimit.OverrideSpeed = 20
	s.NextHazard.Value = "old hazard"
	s.MapCurveSpeed = 9
	s.DistanceSinceLastPosition = 8
	second := syntheticSample(t, cereal.GpsSourceInternal, 20_000, 2, true, true)
	boot = 20_001
	newTile := syntheticTile(t, 8, true)
	s.ProcessGps(second, true, func(m.Position) (maps.Offline, error) { return newTile, nil }, now.Add(time.Second))
	_, out := decodedOutput(t, &s)
	if out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit || out.GpsSource() != custom.MapdOut_GpsSource_internal || out.SourceGeneration() != 2 || math.Abs(float64(out.SpeedLimit()-8)) > 0.001 || s.SpeedLimit.AcceptedLimit != 0 || s.SpeedLimit.OverrideSpeed != 0 || s.NextHazard.Value != "" || s.MapCurveSpeed != 0 || s.DistanceSinceLastPosition != 0 {
		t.Fatalf("source switch retained old derived state: status=%v speed=%f accepted=%f hazard=%q", out.RoadStatus(), out.SpeedLimit(), s.SpeedLimit.AcceptedLimit, s.NextHazard.Value)
	}
}

func TestSlowTileLoadExpiresGpsBeforePublication(t *testing.T) {
	s := State{}
	s.Init()
	fix := uint64(10_000_000_000)
	boot := fix + 100_000_000
	s.bootNow = func() uint64 { return boot }
	sample := syntheticSample(t, cereal.GpsSourceExternal, fix, 7, true, true)
	tile := syntheticTile(t, 13, true)
	s.ProcessGps(sample, true, func(m.Position) (maps.Offline, error) {
		boot = fix + 500_000_001 // synthetic loader delay, no wall-clock sleep
		return tile, nil
	}, time.Unix(0, 0))
	event, out := decodedOutput(t, &s)
	if event.Valid() || event.LogMonoTime() != boot || out.RoadStatus() != custom.MapdOut_SampleStatus_noGps || out.GpsMonoTime() != fix || out.GpsSource() != custom.MapdOut_GpsSource_external || out.SourceGeneration() != 7 || out.ProducerSession() == 0 || out.SpeedLimit() != 0 || out.WayId() != 0 || s.DistanceSinceLastPosition != 0 || s.Data.Loaded {
		t.Fatalf("slow loader published stale road: valid=%v status=%v source=%v gps=%d generation=%d limit=%f", event.Valid(), out.RoadStatus(), out.GpsSource(), out.GpsMonoTime(), out.SourceGeneration(), out.SpeedLimit())
	}
	_, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	extEvent, err := log.NewRootEvent(seg)
	if err != nil {
		t.Fatal(err)
	}
	extOut, err := extEvent.NewMapdExtendedOut()
	if err != nil {
		t.Fatal(err)
	}
	ext := ExtendedState{state: &s}
	ext.setPath(extOut)
	ext.setPosition(extOut)
	path, err := extOut.Path()
	if err != nil || path.Len() != 0 || extOut.HasPosition() {
		t.Fatal("expired road leaked into extended output")
	}
}

func TestDelayedSerializationRechecksOriginalFixAge(t *testing.T) {
	s := State{}
	s.Init()
	fix := uint64(20_000_000_000)
	boot := fix + 100_000_000
	s.bootNow = func() uint64 { return boot }
	sample := syntheticSample(t, cereal.GpsSourceInternal, fix, 3, true, true)
	tile := syntheticTile(t, 8, true)
	s.ProcessGps(sample, true, func(m.Position) (maps.Offline, error) { return tile, nil }, time.Unix(0, 0))
	if !s.RoadMatched() {
		t.Fatal("pre-delay sample was not matched")
	}
	boot = fix + 2_000_000_000
	event, out := decodedOutput(t, &s)
	if !event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit {
		t.Fatal("exact internal TTL edge rejected")
	}
	boot++ // delay between computation and next serialization
	event, out = decodedOutput(t, &s)
	if event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_noGps || out.GpsMonoTime() != fix || out.SourceGeneration() != 3 || out.SpeedLimit() != 0 || out.WayId() != 0 || s.Position.Lat() != 0 || s.Position.Lon() != 0 {
		t.Fatalf("delayed serialization retained stale limit: valid=%v status=%v gps=%d limit=%f", event.Valid(), out.RoadStatus(), out.GpsMonoTime(), out.SpeedLimit())
	}
}

func TestSerializationCrossingGpsTtlDiscardsValidWireMessage(t *testing.T) {
	s := State{}
	s.Init()
	fix := uint64(30_000_000_000)
	s.bootNow = func() uint64 { return fix + 100_000_000 }
	sample := syntheticSample(t, cereal.GpsSourceExternal, fix, 5, true, true)
	tile := syntheticTile(t, 13, true)
	s.ProcessGps(sample, true, func(m.Position) (maps.Offline, error) { return tile, nil }, time.Unix(0, 0))
	if !s.RoadMatched() {
		t.Fatal("pre-serialization road did not match")
	}
	clockReads := 0
	s.bootNow = func() uint64 {
		clockReads++
		if clockReads == 1 {
			return fix + 100_000_000
		}
		return fix + 500_000_001
	}
	event, out := decodedOutput(t, &s)
	if clockReads < 2 || event.Valid() || event.LogMonoTime() != fix+500_000_001 || out.RoadStatus() != custom.MapdOut_SampleStatus_noGps || out.SpeedLimit() != 0 || out.WayId() != 0 || out.GpsMonoTime() != fix || out.SourceGeneration() != 5 {
		t.Fatalf("expired during serialization: reads=%d valid=%v mono=%d status=%v limit=%f", clockReads, event.Valid(), event.LogMonoTime(), out.RoadStatus(), out.SpeedLimit())
	}
}

func TestSyntheticCoverageAndNoMatchFailures(t *testing.T) {
	now := time.Unix(0, 0)
	sample := syntheticSample(t, cereal.GpsSourceInternal, 10_000, 1, true, true)
	for name, loader := range map[string]MapLoader{
		"missing":    func(m.Position) (maps.Offline, error) { return maps.Offline{}, nil },
		"read error": func(m.Position) (maps.Offline, error) { return syntheticTile(t, 13, true), errors.New("corrupt") },
	} {
		t.Run(name, func(t *testing.T) {
			s := State{}
			s.Init()
			s.bootNow = func() uint64 { return 10_001 }
			s.ProcessGps(sample, true, loader, now)
			event, out := decodedOutput(t, &s)
			if event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_noCoverage || out.SpeedLimit() != 0 || out.WayId() != 0 {
				t.Fatalf("unavailable tile emitted road: %v %v", event.Valid(), out.RoadStatus())
			}
		})
	}
	s := State{}
	s.Init()
	s.bootNow = func() uint64 { return 10_001 }
	s.ProcessGps(sample, true, func(m.Position) (maps.Offline, error) { return syntheticTile(t, 13, false), nil }, now)
	event, out := decodedOutput(t, &s)
	if event.Valid() || out.RoadStatus() != custom.MapdOut_SampleStatus_noMatch || out.SpeedLimit() != 0 || out.WayId() != 0 {
		t.Fatalf("no matching way emitted road: %v %v", event.Valid(), out.RoadStatus())
	}
}

func TestExtendedRoadEvidenceClearsWhileDiagnosticsRemain(t *testing.T) {
	s := State{}
	s.Init()
	_, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.NewRootEvent(seg)
	if err != nil {
		t.Fatal(err)
	}
	out, err := event.NewMapdExtendedOut()
	if err != nil {
		t.Fatal(err)
	}
	extended := ExtendedState{state: &s}
	extended.setPath(out)
	extended.setPosition(out)
	path, err := out.Path()
	if err != nil || path.Len() != 0 {
		t.Fatal("invalid road path not cleared")
	}
	if out.HasPosition() {
		t.Fatal("missing GPS leaked old position")
	}
}

func TestCarGpsUnknownDirectionCannotPublishRoadLimit(t *testing.T) {
	s := State{}
	s.Init()
	fix := uint64(10_000_000_000)
	s.bootNow = func() uint64 { return fix + 100_000_000 }
	sample := syntheticSample(t, cereal.GpsSourceCar, fix, 1, true, true)
	tile := syntheticTile(t, 13.4112, true)
	loader := func(m.Position) (maps.Offline, error) { return tile, nil }
	sample.Location.SetBearingAccuracyDeg(1)
	sample.Location.SetSpeedAccuracy(1)
	s.ProcessGps(sample, true, loader, time.Unix(0, 0))
	_, out := decodedOutput(t, &s)
	if out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit || out.GpsSource() != custom.MapdOut_GpsSource_car {
		t.Fatal("measured car direction rejected")
	}
	for _, unknown := range []string{"bearing", "speed"} {
		sample.Location.SetBearingAccuracyDeg(1)
		sample.Location.SetSpeedAccuracy(1)
		if unknown == "bearing" {
			sample.Location.SetBearingAccuracyDeg(180)
		} else {
			sample.Location.SetSpeedAccuracy(100)
		}
		s.ProcessGps(sample, true, loader, time.Unix(0, 0))
		_, out = decodedOutput(t, &s)
		if out.RoadStatus() != custom.MapdOut_SampleStatus_noMatch || out.SpeedLimit() != 0 || out.WayId() != 0 || out.GpsSource() != custom.MapdOut_GpsSource_car {
			t.Fatal("unknown uncertainty retained confident evidence", unknown)
		}
	}
	sample.Source = cereal.GpsSourceExternal
	s.ProcessGps(sample, true, loader, time.Unix(0, 0))
	_, out = decodedOutput(t, &s)
	if out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit {
		t.Fatal("hardware behavior changed")
	}
}
