package maps

import (
	"bytes"
	"errors"
	"io"
	"log/slog"
	"math"
	"os"
	"unicode/utf8"

	"pfeifer.dev/mapd/cereal/offline"
	m "pfeifer.dev/mapd/math"
	u "pfeifer.dev/mapd/utils"

	"capnproto.org/go/capnp/v3"
)

// The decoder's normal message limit is 64 MiB. Packed data can carry up to
// nine bytes per eight decoded bytes, plus framing. This also bounds reads
// before the streaming decoder sees an untrusted tile.
const maxOfflineMessageBytes = 64 << 20
const maxOfflinePackedBytes = 73 << 20
const maxOfflineValidationTraversalBytes = 256 << 20

func ReadOffline(data []uint8) Offline {
	if len(data) > maxOfflinePackedBytes {
		return Offline{}
	}
	decoder := capnp.NewPackedDecoder(bytes.NewReader(data))
	decoder.MaxMessageSize = maxOfflineMessageBytes
	msg, err := decoder.Decode()
	if err != nil {
		slog.Warn("could not unmarshal offline data", "error", err)
		return Offline{}
	}
	if _, err := decoder.Decode(); !errors.Is(err, io.EOF) {
		slog.Warn("could not read offline message", "reason", "trailing packed data", "error", err)
		return Offline{}
	}
	// Validation touches every field, sometimes through repeated pointers.
	// Keep this phase finite and separate from the decoded-size ceiling.
	msg.ResetReadLimit(maxOfflineValidationTraversalBytes)
	offlineMaps, err := offline.ReadRootOffline(msg)
	if err != nil {
		slog.Warn("could not read offline message", "error", err)
		return Offline{Loaded: false}
	}
	if !offlineMaps.IsValid() {
		slog.Warn("could not read offline message", "reason", "root is not a struct")
		return Offline{Loaded: false}
	}
	if !validOfflineBounds(offlineMaps) {
		slog.Warn("could not read offline message", "reason", "invalid geographic bounds")
		return Offline{Loaded: false}
	}
	ways, err := offlineMaps.Ways()
	if err != nil {
		slog.Warn("Could not read ways from offline maps", "error", err)
		return Offline{Loaded: false}
	}
	if !ways.IsValid() {
		slog.Warn("could not read offline message", "reason", "ways is not a list")
		return Offline{Loaded: false}
	}
	if !validOfflineWays(ways) {
		slog.Warn("could not read offline message", "reason", "invalid nested way data")
		return Offline{}
	}
	// All reachable pointers and values have been traversed under the
	// bounded budget above. Curry-backed map operations revisit this same
	// immutable message indefinitely, so only this validated graph can
	// have its traversal budget reset for repeated reads.
	msg.ResetReadLimit(math.MaxUint64)
	o := Offline{offline: offlineMaps, waysRaw: ways, Loaded: true}
	o.Ways.Init(o._wayAt, ways.Len())
	o.buildWayIndexes()
	return o
}

func validCoordinate(lat, lon float64) bool {
	return !math.IsNaN(lat) && !math.IsInf(lat, 0) && lat >= -90 && lat <= 90 &&
		!math.IsNaN(lon) && !math.IsInf(lon, 0) && lon >= -180 && lon <= 180
}

func validSpeed(v float64) bool {
	return !math.IsNaN(v) && !math.IsInf(v, 0) && v >= 0 && v <= math.MaxFloat32
}

func validOfflineWays(ways offline.Way_List) bool {
	for i := 0; i < ways.Len(); i++ {
		way := ways.At(i)
		waySize := capnp.Struct(way).Size()
		// The original road fields through ID occupy 80 data bytes and four
		// pointers (name, ref, nodes, hazard). Conditional text pointers were
		// appended later and must remain optional for older offline tiles.
		if !way.IsValid() || waySize.DataSize < 80 || waySize.PointerCount < 4 ||
			way.Id() <= 0 || way.HighwayClass() > offline.HighwayClass_livingStreet ||
			!validSpeed(way.MaxSpeed()) || !validSpeed(way.MaxSpeedForward()) ||
			!validSpeed(way.MaxSpeedBackward()) || !validSpeed(way.AdvisorySpeed()) {
			return false
		}
		minLat, maxLat, minLon, maxLon := way.MinLat(), way.MaxLat(), way.MinLon(), way.MaxLon()
		if !validCoordinate(minLat, minLon) || !validCoordinate(maxLat, maxLon) || minLat > maxLat || minLon > maxLon {
			return false
		}
		for _, index := range []uint16{0, 1, 3, 4, 5, 6} {
			ptr, err := capnp.Struct(way).Ptr(index)
			if err != nil {
				return false
			}
			if !ptr.IsValid() { // Optional missing text is the generator default.
				continue
			}
			list := ptr.List()
			if !list.IsValid() || list.Len() == 0 || ptr.TextBytes() == nil ||
				capnp.UInt8List(list).At(list.Len()-1) != 0 || !utf8.Valid(ptr.TextBytes()) {
				return false
			}
		}
		nodes, err := way.Nodes()
		if err != nil || !nodes.IsValid() || nodes.Len() < 2 {
			return false
		}
		for j := 0; j < nodes.Len(); j++ {
			node := nodes.At(j)
			if !node.IsValid() || capnp.Struct(node).Size().DataSize < 16 {
				return false
			}
			lat, lon := node.Latitude(), node.Longitude()
			if !validCoordinate(lat, lon) || lat < minLat || lat > maxLat || lon < minLon || lon > maxLon {
				return false
			}
		}
	}
	return true
}

func validOfflineBounds(tile offline.Offline) bool {
	minLat, maxLat := tile.MinLat(), tile.MaxLat()
	minLon, maxLon := tile.MinLon(), tile.MaxLon()
	overlap := tile.Overlap()
	for _, value := range []float64{minLat, maxLat, minLon, maxLon, overlap} {
		if math.IsNaN(value) || math.IsInf(value, 0) {
			return false
		}
	}
	return minLat >= -90 && maxLat <= 90 && minLat < maxLat &&
		minLon >= -180 && maxLon <= 180 && minLon < maxLon && overlap >= 0
}

// SourceCurrent reports whether a path-backed tile is still the same regular
// file that passed validation. In-memory synthetic tiles have no source path.
func (o *Offline) SourceCurrent() bool {
	if !o.Loaded || o.sourcePath == "" {
		return true
	}
	info, err := os.Lstat(o.sourcePath)
	return err == nil && info.Mode().IsRegular() && sameOfflineFile(o.sourceInfo, info)
}

// SourceCurrentFor also binds a cached tile to the receipt that verified it.
// An ordinary-mode or older-generation cache cannot satisfy a new snapshot.
func (o *Offline) SourceCurrentFor(snapshotID string) bool {
	return o.snapshotID == snapshotID && o.SourceCurrent()
}

type Offline struct {
	Loaded     bool
	sourcePath string
	sourceInfo os.FileInfo
	snapshotID string
	offline    offline.Offline
	box        u.Curry[m.Box]
	overlapBox u.Curry[m.Box]
	Ways       u.CurryList[Way]
	waysRaw    offline.Way_List
	overlap    u.Curry[float64]
	grid       *wayGrid               // padded way boxes by cell, see way_index.go
	endpoints  map[m.Position][]int32 // way indices by first/last node
}

func (o *Offline) _box() m.Box {
	return m.Box{
		MinPos: m.NewPosition(float64(o.offline.MinLat()), float64(o.offline.MinLon())),
		MaxPos: m.NewPosition(float64(o.offline.MaxLat()), float64(o.offline.MaxLon())),
	}
}

func (o *Offline) Box() m.Box {
	return o.box.Value(o._box)
}

func (o *Offline) _overlapBox() m.Box {
	box := o.Box()
	return box.Overlap(o.Overlap())
}

func (o *Offline) OverlapBox() m.Box {
	return o.overlapBox.Value(o._overlapBox)
}

func (o *Offline) _overlap() float64 {
	return o.offline.Overlap()
}

func (o *Offline) Overlap() float64 {
	return o.overlap.Value(o._overlap)
}

func (o *Offline) _wayAt(index int) Way {
	return NewWay(o.waysRaw.At(index))
}
