package maps

import (
	"encoding/binary"
	"math"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"

	m "pfeifer.dev/mapd/math"

	"capnproto.org/go/capnp/v3"
	"capnproto.org/go/capnp/v3/packed"
	"pfeifer.dev/mapd/cereal/offline"
)

func testOfflineTile(t *testing.T, edit func(offline.Offline, *capnp.Segment)) []byte {
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
	if _, err := tile.NewWays(0); err != nil {
		t.Fatal(err)
	}
	if edit != nil {
		edit(tile, seg)
	}
	data, err := msg.MarshalPacked()
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func validTestWay(t *testing.T, tile offline.Offline) offline.Way {
	t.Helper()
	ways, err := tile.NewWays(1)
	if err != nil {
		t.Fatal(err)
	}
	w := ways.At(0)
	w.SetId(42)
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
	return w
}

func TestOfflineRejectsMalformedWays(t *testing.T) {
	for _, kind := range []string{"struct", "absent"} {
		t.Run(kind, func(t *testing.T) {
			data := testOfflineTile(t, func(tile offline.Offline, seg *capnp.Segment) {
				var pointer capnp.Ptr
				if kind == "struct" {
					wrong, err := capnp.NewStruct(seg, capnp.ObjectSize{DataSize: 8})
					if err != nil {
						t.Fatal(err)
					}
					pointer = wrong.ToPtr()
				}
				if err := capnp.Struct(tile).SetPtr(0, pointer); err != nil {
					t.Fatal(err)
				}
			})
			if ReadOffline(data).Loaded {
				t.Fatal("malformed or missing ways accepted as loaded")
			}
		})
	}
}

func TestOfflineRejectsInvalidBounds(t *testing.T) {
	cases := map[string]func(offline.Offline){
		"nan":               func(tile offline.Offline) { tile.SetMinLat(math.NaN()) },
		"infinity":          func(tile offline.Offline) { tile.SetMaxLon(math.Inf(1)) },
		"latitude range":    func(tile offline.Offline) { tile.SetMinLat(-91) },
		"longitude range":   func(tile offline.Offline) { tile.SetMaxLon(181) },
		"reversed latitude": func(tile offline.Offline) { tile.SetMinLat(36) },
		"zero width":        func(tile offline.Offline) { tile.SetMinLon(tile.MaxLon()) },
		"negative overlap":  func(tile offline.Offline) { tile.SetOverlap(-1) },
		"nonfinite overlap": func(tile offline.Offline) { tile.SetOverlap(math.NaN()) },
	}
	for name, edit := range cases {
		t.Run(name, func(t *testing.T) {
			data := testOfflineTile(t, func(tile offline.Offline, _ *capnp.Segment) { edit(tile) })
			if ReadOffline(data).Loaded {
				t.Fatal("invalid bounds accepted as loaded")
			}
		})
	}
}

func TestOfflineAcceptsEmptyCoverageAndReadsWay(t *testing.T) {
	empty := ReadOffline(testOfflineTile(t, nil))
	if !empty.Loaded || empty.Ways.Len() != 0 {
		t.Fatal("valid empty coverage rejected")
	}
	data := testOfflineTile(t, func(tile offline.Offline, seg *capnp.Segment) {
		ways, err := tile.NewWays(1)
		if err != nil {
			t.Fatal(err)
		}
		way := ways.At(0)
		way.SetId(42)
		way.SetMaxSpeed(13.4112)
		way.SetMinLat(35.1)
		way.SetMaxLat(35.2)
		way.SetMinLon(-97.9)
		way.SetMaxLon(-97.9)
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
	})
	parsed := ReadOffline(data)
	if !parsed.Loaded || parsed.Ways.Len() != 1 {
		t.Fatal("valid way rejected")
	}
	way := parsed.Ways.At(0)
	if way.Id() != 42 || way.MaxSpeed() != 13.4112 || way.WayName() != "Synthetic road" || way.Nodes.Len() != 2 {
		t.Fatal("way changed during parsing")
	}
}

func TestOfflineRejectsTruncatedPayload(t *testing.T) {
	payload := testOfflineTile(t, nil)
	for _, data := range [][]byte{nil, payload[:len(payload)/2], {0xff, 0xff}} {
		if ReadOffline(data).Loaded {
			t.Fatal("unreadable packed data accepted as loaded")
		}
	}
}

func TestOfflineRejectsNestedInvalidValues(t *testing.T) {
	cases := map[string]func(offline.Way){
		"node nan":              func(w offline.Way) { nodes, _ := w.Nodes(); nodes.At(0).SetLatitude(math.NaN()) },
		"node out of range":     func(w offline.Way) { nodes, _ := w.Nodes(); nodes.At(0).SetLongitude(181) },
		"node outside way":      func(w offline.Way) { w.SetMaxLat(35.15) },
		"limit infinity":        func(w offline.Way) { w.SetMaxSpeed(math.Inf(1)) },
		"limit negative":        func(w offline.Way) { w.SetMaxSpeedBackward(-1) },
		"limit unrepresentable": func(w offline.Way) { w.SetAdvisorySpeed(math.MaxFloat64) },
		"unknown class":         func(w offline.Way) { w.SetHighwayClass(255) },
		"zero identifier":       func(w offline.Way) { w.SetId(0) },
		"one node":              func(w offline.Way) { _, _ = w.NewNodes(1) },
		"missing nodes":         func(w offline.Way) { _ = capnp.Struct(w).SetPtr(2, capnp.Ptr{}) },
		"wrong node pointer":    func(w offline.Way) { _ = capnp.Struct(w).SetPtr(2, capnp.Struct(w).ToPtr()) },
		"wrong text pointer":    func(w offline.Way) { _ = capnp.Struct(w).SetPtr(0, capnp.Struct(w).ToPtr()) },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			data := testOfflineTile(t, func(tile offline.Offline, _ *capnp.Segment) { mutate(validTestWay(t, tile)) })
			if ReadOffline(data).Loaded {
				t.Fatal("invalid nested way accepted")
			}
		})
	}
}

func TestOfflineRejectsWrongNestedListShapes(t *testing.T) {
	cases := []struct {
		name     string
		index    uint16
		makeList func(*capnp.Segment) (capnp.Ptr, error)
	}{
		{"byte nodes", 2, func(seg *capnp.Segment) (capnp.Ptr, error) {
			l, err := capnp.NewUInt8List(seg, 2)
			return l.ToPtr(), err
		}},
		{"uint64 nodes", 2, func(seg *capnp.Segment) (capnp.Ptr, error) {
			l, err := capnp.NewUInt64List(seg, 2)
			return l.ToPtr(), err
		}},
		{"void nodes", 2, func(seg *capnp.Segment) (capnp.Ptr, error) { return capnp.NewVoidList(seg, 2).ToPtr(), nil }},
		{"short composite nodes", 2, func(seg *capnp.Segment) (capnp.Ptr, error) {
			l, err := capnp.NewCompositeList(seg, capnp.ObjectSize{DataSize: 8}, 2)
			return l.ToPtr(), err
		}},
		{"uint64 text", 0, func(seg *capnp.Segment) (capnp.Ptr, error) {
			l, err := capnp.NewUInt64List(seg, 2)
			return l.ToPtr(), err
		}},
		{"composite text", 0, func(seg *capnp.Segment) (capnp.Ptr, error) {
			l, err := capnp.NewCompositeList(seg, capnp.ObjectSize{DataSize: 16}, 2)
			return l.ToPtr(), err
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			data := testOfflineTile(t, func(tile offline.Offline, seg *capnp.Segment) {
				way := validTestWay(t, tile)
				ptr, err := tc.makeList(seg)
				if err != nil {
					t.Fatal(err)
				}
				if err := capnp.Struct(way).SetPtr(tc.index, ptr); err != nil {
					t.Fatal(err)
				}
			})
			if ReadOffline(data).Loaded {
				t.Fatal("wrong nested wire type accepted")
			}
		})
	}
}

func TestOfflineAllowsAppendCompatibleCoordinateLayout(t *testing.T) {
	data := testOfflineTile(t, func(tile offline.Offline, seg *capnp.Segment) {
		way := validTestWay(t, tile)
		larger, err := capnp.NewCompositeList(seg, capnp.ObjectSize{DataSize: 24, PointerCount: 1}, 2)
		if err != nil {
			t.Fatal(err)
		}
		if err := capnp.Struct(way).SetPtr(2, larger.ToPtr()); err != nil {
			t.Fatal(err)
		}
		nodes, err := way.Nodes()
		if err != nil {
			t.Fatal(err)
		}
		nodes.At(0).SetLatitude(35.1)
		nodes.At(0).SetLongitude(-97.9)
		nodes.At(1).SetLatitude(35.2)
		nodes.At(1).SetLongitude(-97.9)
	})
	if !ReadOffline(data).Loaded {
		t.Fatal("append-compatible coordinate struct rejected")
	}
}

func TestOfflineAcceptsHistoricalFourPointerWay(t *testing.T) {
	data := testOfflineTile(t, func(tile offline.Offline, seg *capnp.Segment) {
		// The pre-conditional layout has the original 80-byte scalar area
		// through ID but only name/ref/nodes/hazard pointer slots.
		list, err := capnp.NewCompositeList(seg, capnp.ObjectSize{DataSize: 80, PointerCount: 4}, 1)
		if err != nil {
			t.Fatal(err)
		}
		if err := capnp.Struct(tile).SetPtr(0, list.ToPtr()); err != nil {
			t.Fatal(err)
		}
		w := offline.Way(list.Struct(0))
		w.SetId(42)
		w.SetMaxSpeed(13.4)
		w.SetMinLat(35.1)
		w.SetMaxLat(35.2)
		w.SetMinLon(-97.9)
		w.SetMaxLon(-97.9)
		if err := w.SetName("Historical road"); err != nil {
			t.Fatal(err)
		}
		if err := w.SetRef("H1"); err != nil {
			t.Fatal(err)
		}
		nodes, err := w.NewNodes(2)
		if err != nil {
			t.Fatal(err)
		}
		nodes.At(0).SetLatitude(35.1)
		nodes.At(0).SetLongitude(-97.9)
		nodes.At(1).SetLatitude(35.2)
		nodes.At(1).SetLongitude(-97.9)
	})
	parsed := ReadOffline(data)
	if !parsed.Loaded || parsed.Ways.Len() != 1 {
		t.Fatal("historical tile rejected")
	}
	w := parsed.Ways.At(0)
	if w.Id() != 42 || w.MaxSpeed() != 13.4 || w.WayName() != "Historical road" || w.WayRef() != "H1" || w.Nodes.Len() != 2 ||
		w.HighwayClass() != offline.HighwayClass_unknown || w.MaxSpeedConditional() != "" ||
		w.MaxSpeedForwardConditional() != "" || w.MaxSpeedBackwardConditional() != "" {
		t.Fatal("historical geometry or absent optional fields changed")
	}
}

func TestOfflineRejectsTrailingOrOversizeAndReusesValidatedGraph(t *testing.T) {
	valid := testOfflineTile(t, func(tile offline.Offline, _ *capnp.Segment) {
		w := validTestWay(t, tile)
		if err := w.SetName(strings.Repeat("x", 2048)); err != nil {
			t.Fatal(err)
		}
	})
	if ReadOffline(append(append([]byte{}, valid...), valid...)).Loaded {
		t.Fatal("second message accepted")
	}
	if ReadOffline(append(append([]byte{}, valid...), 0xff)).Loaded {
		t.Fatal("trailing garbage accepted")
	}
	if ReadOffline(make([]byte, maxOfflinePackedBytes+1)).Loaded {
		t.Fatal("oversize packed message accepted")
	}
	var largeHeader [8]byte
	binary.LittleEndian.PutUint32(largeHeader[4:], 1<<24) // declares 128 MiB
	if ReadOffline(packed.Pack(nil, largeHeader[:])).Loaded {
		t.Fatal("oversize decoded message header accepted")
	}
	tile := ReadOffline(valid)
	if !tile.Loaded {
		t.Fatal("valid tile rejected")
	}
	// Repeated pointer reads exceed the one-time 256 MiB validation budget.
	for i := 0; i < 150_000; i++ {
		name, err := tile.waysRaw.At(0).Name()
		if err != nil || len(name) != 2048 {
			t.Fatalf("cached read %d: %v", i, err)
		}
	}
}

func TestOfflinePathRequiresExactAreaAndCurrentRegularFile(t *testing.T) {
	old := DEFAULT_SETTINGS.OutputDirectory
	defer func() { DEFAULT_SETTINGS.OutputDirectory = old }()
	DEFAULT_SETTINGS.OutputDirectory = t.TempDir()
	pos := m.NewPosition(35.15, -97.9)
	area := Area{Box: m.Box{MinPos: m.NewPosition(35, -98), MaxPos: m.NewPosition(35.25, -97.75)}}
	path := GenerateBoundsFileName(area, DEFAULT_SETTINGS)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	wrong := testOfflineTile(t, func(tile offline.Offline, _ *capnp.Segment) { tile.SetMaxLat(35.5) })
	if err := os.WriteFile(path, wrong, 0644); err != nil {
		t.Fatal(err)
	}
	loaded, err := FindWaysAroundPosition(pos)
	if err != nil || loaded.Loaded {
		t.Fatalf("wrong area accepted: loaded=%v err=%v", loaded.Loaded, err)
	}
	valid := testOfflineTile(t, nil)
	if err := os.WriteFile(path, valid, 0644); err != nil {
		t.Fatal(err)
	}
	loaded, err = FindWaysAroundPosition(pos)
	if err != nil || !loaded.Loaded || !loaded.SourceCurrent() {
		t.Fatalf("valid path: loaded=%v err=%v", loaded.Loaded, err)
	}
	stage := path + ".stage"
	if err := os.WriteFile(stage, valid, 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(stage, path); err != nil {
		t.Fatal(err)
	}
	if loaded.SourceCurrent() {
		t.Fatal("atomic replacement retained cache identity")
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(stage, path); err != nil {
		t.Fatal(err)
	}
	if _, err := FindWaysAroundPosition(pos); err == nil {
		t.Fatal("symlink tile accepted")
	}
}

func TestOfflinePathRejectsFifoWithoutBlocking(t *testing.T) {
	old := DEFAULT_SETTINGS.OutputDirectory
	defer func() { DEFAULT_SETTINGS.OutputDirectory = old }()
	DEFAULT_SETTINGS.OutputDirectory = t.TempDir()
	pos := m.NewPosition(35.15, -97.9)
	area := Area{Box: m.Box{MinPos: m.NewPosition(35, -98), MaxPos: m.NewPosition(35.25, -97.75)}}
	path := GenerateBoundsFileName(area, DEFAULT_SETTINGS)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := syscall.Mkfifo(path, 0600); err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() { _, err := FindWaysAroundPosition(pos); done <- err }()
	select {
	case err := <-done:
		if err == nil {
			t.Fatal("FIFO accepted as a tile")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("FIFO open blocked before special-file rejection")
	}
}
