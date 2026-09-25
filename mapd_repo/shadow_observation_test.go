package main

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"capnproto.org/go/capnp/v3"
	"github.com/pfeiferj/gomsgq"
	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
)

func shadowOutput(t *testing.T, state *State, read func() (cereal.GpsSample, bool), load MapLoader, now time.Time) (log.Event, custom.MapdOut) {
	t.Helper()
	msg, err := shadowStep(state, read, load, now)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := msg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := capnp.Unmarshal(raw)
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

func TestShadowExplicitRootActualTileLoop(t *testing.T) {
	root := t.TempDir()
	defaultRoot := maps.DEFAULT_SETTINGS.OutputDirectory
	area := maps.Area{Box: m.Box{MinPos: m.NewPosition(35, -98), MaxPos: m.NewPosition(35.25, -97.75)}}
	path := maps.GenerateBoundsFileName(area, maps.OfflineSettings{OutputDirectory: root})
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, diskTileBytes(t, 13), 0644); err != nil {
		t.Fatal(err)
	}
	state := State{ShadowOnly: true}
	state.Init()
	boot := uint64(10_100_000_000)
	state.bootNow = func() uint64 { return boot }
	load := func(pos m.Position) (maps.Offline, error) { return maps.FindWaysAroundPositionIn(pos, root) }
	sample := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
	event, out := shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true }, load, time.Unix(0, 0))
	if !event.Valid() || out.SpeedLimit() != 13 || out.RoadStatus() != custom.MapdOut_SampleStatus_matchedLimit || out.ProducerSession() == 0 {
		t.Fatalf("shadow tile candidate missing: valid=%v status=%v limit=%f", event.Valid(), out.RoadStatus(), out.SpeedLimit())
	}
	if out.SuggestedSpeed() != 0 || out.SpeedLimitSuggestedSpeed() != 0 || out.SpeedLimitAccepted() || out.NextSpeedLimit() != 0 || out.NextHazardDistance() != 0 || out.NextAdvisorySpeed() != 0 || out.MapCurveSpeed() != 0 || out.VisionCurveSpeed() != 0 {
		t.Fatal("shadow published control-derived fields")
	}
	sample.SourceChanged, sample.NewFix = false, false
	_, out = shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true }, load, time.Unix(0, 1))
	if out.GpsMonoTime() != 10_000_000_000 || out.SpeedLimit() != 13 {
		t.Fatal("same-fix observation not retained")
	}
	boot = 10_600_000_000
	event, out = shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true }, load, time.Unix(0, 2))
	if event.Valid() || out.SpeedLimit() != 0 || out.WayId() != 0 {
		t.Fatal("expired fix retained candidate")
	}
	if _, _, err := shadowRoot([]string{"--offline-root", filepath.Join(root, "missing")}); err == nil {
		t.Fatal("missing root accepted")
	}
	if _, err := maps.AdmitSnapshot(context.Background(), maps.AdmitOptions{Root: root, Bounds: [4]float64{35, -98, 35.25, -97.75}, Overlap: .001,
		PBF: filepath.Join("testdata", "synthetic_snapshot.osm.pbf"), SourceRevision: "test", UpstreamRevision: "test", SourceDigest: "test"}); err != nil {
		t.Fatal(err)
	}
	if _, _, err := shadowRoot([]string{"--offline-root", root}); err != nil {
		t.Fatal(err)
	}
	if maps.DEFAULT_SETTINGS.OutputDirectory != defaultRoot {
		t.Fatal("shadow root changed the ordinary provider default")
	}
	link := filepath.Join(t.TempDir(), "tile-link")
	if err := os.Symlink(root, link); err != nil {
		t.Fatal(err)
	}
	if _, _, err := shadowRoot([]string{"--offline-root", link}); err == nil {
		t.Fatal("symlink root accepted")
	}
}

func TestShadowPumpPublishesActualSerializedStateAndStops(t *testing.T) {
	state := State{ShadowOnly: true}
	state.Init()
	state.bootNow = func() uint64 { return 10_100_000_000 }
	sample := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
	tile := syntheticTile(t, 12, true)
	ticks := make(chan time.Time)
	published := make(chan []byte, 1)
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		runShadowLoop(ctx, ticks, &state, func() (cereal.GpsSample, bool) { return sample, true },
			func(m.Position) (maps.Offline, error) { return tile, nil }, func(msg *capnp.Message) error {
				raw, err := msg.Marshal()
				if err == nil {
					published <- raw
				}
				return err
			})
	}()
	ticks <- time.Unix(0, 0)
	raw := <-published
	decoded, err := capnp.Unmarshal(raw)
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
	if !event.Valid() || out.SpeedLimit() != 12 || out.SuggestedSpeed() != 0 || out.SpeedLimitAccepted() {
		t.Fatal("shadow pump serialized unexpected observation")
	}
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("shadow pump did not stop")
	}
}

func TestPinnedSnapshotTileCorruptionClearsRunningShadow(t *testing.T) {
	root := t.TempDir()
	id, err := maps.AdmitSnapshot(context.Background(), maps.AdmitOptions{Root: root, Bounds: [4]float64{35, -98, 35.25, -97.75}, Overlap: .001,
		PBF: filepath.Join("testdata", "synthetic_snapshot.osm.pbf"), SourceRevision: "test", UpstreamRevision: "test", SourceDigest: "test"})
	if err != nil {
		t.Fatal(err)
	}
	dir, receipt, err := maps.ResolveSnapshot(root)
	if err != nil {
		t.Fatal(err)
	}
	state := State{ShadowOnly: true, SnapshotID: id}
	state.Init()
	boot := uint64(10_100_000_000)
	state.bootNow = func() uint64 { return boot }
	sample := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
	load := maps.SnapshotLoader(dir, receipt)
	event, out := shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true }, load, time.Unix(0, 1))
	if !event.Valid() || out.SpeedLimit() <= 0 {
		t.Fatal("admitted synthetic tile did not produce diagnostic candidate")
	}
	path := filepath.Join(dir, receipt.Tiles[0].Path)
	if err := os.WriteFile(path, []byte("corrupt"), 0600); err != nil {
		t.Fatal(err)
	}
	boot += 50_000_000
	sample.NewFix, sample.SourceChanged = false, false
	event, out = shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true }, load, time.Unix(0, 2))
	if event.Valid() || out.SpeedLimit() != 0 || out.WayId() != 0 || state.Data.Loaded {
		t.Fatal("changed pinned tile retained road evidence")
	}
}

func TestShadowFreshBundledDefaultsAndParallelAmbiguity(t *testing.T) {
	prior := ms.Settings
	defer func() { ms.Settings = prior }()
	ms.Settings = ms.MapdSettings{}
	if err := initShadowDefaults(); err != nil {
		t.Fatal(err)
	}
	if ms.Settings.DefaultLaneWidth != 3.7 || ms.Settings.SubscriberSettings.ShadowGpsLocation || ms.Settings.SubscriberSettings.ShadowGpsLocationExternal {
		t.Fatalf("wrong bundled shadow defaults: width=%f", ms.Settings.DefaultLaneWidth)
	}
	local := syntheticWay{1, 8, 35.1, -97.9, 35.2, -97.9, false, 2}
	parallel := syntheticWay{2, 30, 35.1, -97.8999, 35.2, -97.8999, false, 6}
	for _, tc := range []struct {
		name string
		ways []syntheticWay
		want custom.MapdOut_SampleStatus
	}{
		{"unique", []syntheticWay{local}, custom.MapdOut_SampleStatus_matchedLimit},
		{"parallel", []syntheticWay{local, parallel}, custom.MapdOut_SampleStatus_unknown},
	} {
		t.Run(tc.name, func(t *testing.T) {
			state := State{ShadowOnly: true}
			state.Init()
			state.bootNow = func() uint64 { return 10_100_000_000 }
			tile := packedRoadTile(t, tc.ways)
			sample := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
			_, out := shadowOutput(t, &state, func() (cereal.GpsSample, bool) { return sample, true },
				func(m.Position) (maps.Offline, error) { return tile, nil }, time.Unix(0, 0))
			if out.RoadStatus() != tc.want {
				t.Fatalf("shadow matcher status %v, want %v", out.RoadStatus(), tc.want)
			}
			if tc.name == "unique" && out.EstimatedRoadWidth() != 7.4 {
				t.Fatalf("bundled lane width not used: %f", out.EstimatedRoadWidth())
			}
			if len(state.NextWays) != 0 || len(state.Curvatures) != 0 || len(state.TargetVelocities) != 0 {
				t.Fatal("shadow calculated unused car/curve outputs")
			}
		})
	}
}

func TestShadowIPCPathAndSizeIgnoreLegacyBootstrap(t *testing.T) {
	oldPrefix, oldUse, oldSize := gomsgq.OPENPILOT_PREFIX, gomsgq.USE_MSGQ_PREFIX, ms.ServiceQueueSize["mapdOut"]
	defer func() {
		gomsgq.OPENPILOT_PREFIX, gomsgq.USE_MSGQ_PREFIX = oldPrefix, oldUse
		ms.ServiceQueueSize["mapdOut"] = oldSize
	}()
	for _, tc := range []struct{ prefix, bootstrap string }{{"", ""}, {"private_fixture", "false"}} {
		t.Setenv("OPENPILOT_PREFIX", tc.prefix)
		t.Setenv("USE_MSGQ_PREFIX", tc.bootstrap)
		gomsgq.OPENPILOT_PREFIX = "stale_old_value"
		gomsgq.USE_MSGQ_PREFIX = "false"
		initShadowIPC()
		if !gomsgq.IsPrefixedMsgq() || gomsgq.OPENPILOT_PREFIX != tc.prefix || ms.GetSegmentSize("mapdOut") != ms.QUEUE_SIZE_SMALL || ms.GetSegmentSize("gpsLocation") != ms.QUEUE_SIZE_SMALL {
			t.Fatalf("shadow host IPC contract failed for prefix %q/bootstrap %q", tc.prefix, tc.bootstrap)
		}
	}
}
