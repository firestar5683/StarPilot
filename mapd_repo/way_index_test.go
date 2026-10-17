package main

import (
	"math/rand"
	"testing"
	"time"

	capnp "capnproto.org/go/capnp/v3"
	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
)

// denseStreetSpecs lays out a city grid of short blocks plus two long
// diagonal roads that span many index cells, all inside the synthetic tile.
func denseStreetSpecs(blocks int) []syntheticWay {
	specs := []syntheticWay{}
	id := int64(1)
	step := 0.2 / float64(blocks)
	for line := 0; line <= blocks; line++ {
		for block := 0; block < blocks; block++ {
			lat, lon := 35.02+float64(line)*step, -97.98+float64(line)*step
			from := float64(block) * step
			specs = append(specs,
				syntheticWay{id, 11, lat, -97.98 + from, lat, -97.98 + from + step, false, 2},
				syntheticWay{id + 1, 11, 35.02 + from, lon, 35.02 + from + step, lon, line%3 == 0, 2})
			id += 2
		}
	}
	return append(specs,
		syntheticWay{id, 30, 35.01, -97.99, 35.24, -97.76, false, 6},
		syntheticWay{id + 1, 30, 35.24, -97.99, 35.01, -97.76, true, 4})
}

func gpsAt(t testing.TB, lat, lon, bearing float64) log.GpsLocationData {
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
	location.SetLatitude(lat)
	location.SetLongitude(lon)
	location.SetBearingDeg(float32(bearing))
	location.SetHorizontalAccuracy(5)
	return location
}

// fullScanPlausibleWays is the pre-index matcher, kept as the reference.
func fullScanPlausibleWays(offlineMaps *maps.Offline, location log.GpsLocationData) []int64 {
	ids := []int64{}
	seen := map[int64]bool{}
	for i := range offlineMaps.Ways.Len() {
		way := offlineMaps.Ways.At(i)
		if way.Id() <= 0 || way.Nodes.Len() < 2 || seen[way.Id()] {
			continue
		}
		onWay, err := way.OnWay(location, 2)
		if err != nil || !onWay.OnWay {
			continue
		}
		seen[way.Id()] = true
		ids = append(ids, way.Id())
	}
	return ids
}

func TestWayGridMatchesFullScan(t *testing.T) {
	tile := packedRoadTile(t, denseStreetSpecs(40))
	random := rand.New(rand.NewSource(7))
	matched := 0
	for range 3000 {
		lat := 35 + random.Float64()*0.25
		lon := -98 + random.Float64()*0.25
		location := gpsAt(t, lat, lon, random.Float64()*359)
		want := fullScanPlausibleWays(&tile, location)
		got := []int64{}
		for _, way := range plausibleLoadedWays(&tile, location) {
			got = append(got, way.Id())
		}
		if len(got) != len(want) {
			t.Fatalf("at %f,%f indexed %v, full scan %v", lat, lon, got, want)
		}
		for i := range got {
			if got[i] != want[i] {
				t.Fatalf("at %f,%f indexed order %v, full scan %v", lat, lon, got, want)
			}
		}
		matched += len(want)
	}
	if matched == 0 {
		t.Fatal("no sample landed on a road; the comparison proved nothing")
	}
}

func TestWayGridCutsCandidates(t *testing.T) {
	tile := packedRoadTile(t, denseStreetSpecs(40))
	candidates, ok := tile.WaysNear(m.NewPosition(35.125, -97.875))
	if !ok || len(candidates) == 0 || len(candidates)*10 > tile.Ways.Len() {
		t.Fatalf("grid returned %d of %d ways (indexed=%v)", len(candidates), tile.Ways.Len(), ok)
	}
	if _, ok := tile.WaysNear(m.NewPosition(36, -97.875)); ok {
		t.Fatal("a position outside the tile must fall back to a full scan")
	}
}

func TestEndpointIndexMatchesFullScan(t *testing.T) {
	tile := packedRoadTile(t, denseStreetSpecs(20))
	for i := range tile.Ways.Len() {
		way := tile.Ways.At(i)
		for _, node := range []m.Position{way.Nodes.At(0), way.Nodes.At(way.Nodes.Len() - 1)} {
			got, err := way.MatchingWays(&tile, node)
			if err != nil {
				t.Fatal(err)
			}
			want := []int64{}
			for j := range tile.Ways.Len() {
				other := tile.Ways.At(j)
				box, ownBox := other.Box(), way.Box()
				first, last := other.Nodes.At(0), other.Nodes.At(other.Nodes.Len()-1)
				if !box.Equals(ownBox) && (first.Equals(node) || last.Equals(node)) {
					want = append(want, other.Id())
				}
			}
			if len(got) != len(want) {
				t.Fatalf("way %d: indexed %d matches, full scan %d", way.Id(), len(got), len(want))
			}
			for k := range got {
				if got[k].Id() != want[k] {
					t.Fatalf("way %d: match order differs", way.Id())
				}
			}
		}
	}
}

func TestRepeatedFixSkipsRoadSearch(t *testing.T) {
	s := State{}
	s.Init()
	s.bootNow = func() uint64 { return 10_100_000_000 }
	tile := syntheticTile(t, 13.4112, true)
	load := func(m.Position) (maps.Offline, error) { return tile, nil }
	sample := syntheticSample(t, cereal.GpsSourceExternal, 10_000_000_000, 1, true, true)
	s.ProcessGps(sample, true, load, time.Unix(0, 0))
	if !s.RoadMatched() || s.CurrentWay.ConfidenceCounter != 1 {
		t.Fatalf("first fix: matched=%v confidence=%d", s.RoadMatched(), s.CurrentWay.ConfidenceCounter)
	}
	sample.NewFix, sample.SourceChanged = false, false
	for range 5 {
		s.ProcessGps(sample, true, load, time.Unix(0, 0))
	}
	if !s.RoadMatched() || s.CurrentWay.ConfidenceCounter != 1 {
		t.Fatalf("a repeated fix searched again: confidence=%d", s.CurrentWay.ConfidenceCounter)
	}
	sample.NewFix, sample.FixMonoTime = true, 10_050_000_000
	s.ProcessGps(sample, true, load, time.Unix(0, 0))
	if s.CurrentWay.ConfidenceCounter != 2 {
		t.Fatalf("a new fix did not search: confidence=%d", s.CurrentWay.ConfidenceCounter)
	}
	// A new source generation always searches, even with an equal timestamp.
	sample.NewFix, sample.SourceGeneration = false, 2
	s.ProcessGps(sample, true, load, time.Unix(0, 0))
	if s.CurrentWay.ConfidenceCounter != 3 {
		t.Fatalf("a new source generation did not search: confidence=%d", s.CurrentWay.ConfidenceCounter)
	}
}

func BenchmarkPlausibleWaysDenseTile(b *testing.B) {
	tile := packedRoadTile(b, denseStreetSpecs(120))
	location := gpsAt(b, 35.1251, -97.8749, 90)
	b.Run("indexed", func(b *testing.B) {
		for range b.N {
			plausibleLoadedWays(&tile, location)
		}
	})
	b.Run("full-scan", func(b *testing.B) {
		for range b.N {
			fullScanPlausibleWays(&tile, location)
		}
	})
}

// referenceOnWay is OnWay's decision without the match-distance prefilter:
// the 0.01 degree box, then the measured distance.
func referenceOnWay(way *maps.Way, location log.GpsLocationData, multiplier float32) bool {
	pos := m.NewPosition(location.Latitude(), location.Longitude())
	box := way.Box()
	oversized := box.Overlap(0.01)
	if !oversized.PosInside(pos) {
		return false
	}
	d, err := way.DistanceFrom(pos)
	if err != nil || !(d.Distance < maps.MatchDistance(location, way.Width(), multiplier)) {
		return false
	}
	return maps.IsForward(d.LineStart, d.LineEnd, float64(location.BearingDeg())) || !way.OneWay()
}

// Fixes are scattered around way nodes out to a few match distances, with
// accuracies from 0 to 400 m, so many land just inside or outside the bound.
func TestMatchPrefilterIsExact(t *testing.T) {
	tile := packedRoadTile(t, denseStreetSpecs(40))
	random := rand.New(rand.NewSource(11))
	near, accepted := 0, 0
	for range 20000 {
		index := random.Intn(tile.Ways.Len())
		way := tile.Ways.At(index)
		node := way.Nodes.At(random.Intn(way.Nodes.Len()))
		accuracy := []float32{0, 3, 5, 12, 40, 400}[random.Intn(6)]
		reach := float64(accuracy+30) * 3 / ms.R * ms.TO_DEGREES
		lat := node.Lat() + (random.Float64()*2-1)*reach
		lon := node.Lon() + (random.Float64()*2-1)*reach
		location := gpsAt(t, lat, lon, random.Float64()*359)
		location.SetHorizontalAccuracy(accuracy)
		for _, multiplier := range []float32{2, way.DistanceMultiplier()} {
			want := referenceOnWay(&way, location, multiplier)
			got, err := way.OnWay(location, multiplier)
			if (err == nil && got.OnWay) != want {
				t.Fatalf("way %d at %f,%f accuracy %v x%v: prefiltered %v, reference %v",
					way.Id(), lat, lon, accuracy, multiplier, got.OnWay, want)
			}
			if want && !tile.WayMayMatch(index, location, multiplier) {
				t.Fatalf("index prefilter rejected way %d that matches at %f,%f", way.Id(), lat, lon)
			}
			if want {
				accepted++
			}
			near++
		}
	}
	if accepted == 0 || accepted == near {
		t.Fatalf("samples did not straddle the bound: %d of %d matched", accepted, near)
	}
}
