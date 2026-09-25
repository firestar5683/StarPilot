package maps

import (
	"math"

	m "pfeifer.dev/mapd/math"
)

// Dense tiles hold hundreds of thousands of ways. The road matcher used to
// test every way in the tile on every 20 Hz loop, and next-way lookups did the
// same for every candidate endpoint. Both indexes below are built once per
// loaded tile and return way indices in tile order, so callers that walk the
// candidates see exactly the ways and order that a full scan would produce.

// WayMatchMargin is the padding Way.OnWay applies to a way's bounding box
// before measuring distance. A way whose padded box misses a position can
// never match it, which is what makes the grid lookup exact.
const WayMatchMargin = 0.01

// wayGridCellDegrees keeps a padded way to a handful of cells while still
// cutting a dense tile's candidate list by one or two orders of magnitude.
const wayGridCellDegrees = 0.01

// wayGridMaxCells bounds the grid for oversized or unusual tile boxes.
// A 0.25 degree tile plus overlap uses about 700 cells.
const wayGridMaxCells = 1 << 16

type wayGrid struct {
	minLat, minLon float64
	rows, cols     int
	cells          [][]int32
}

func (g *wayGrid) cell(lat, lon float64) (row, col int, ok bool) {
	if g == nil || math.IsNaN(lat) || math.IsNaN(lon) {
		return 0, 0, false
	}
	row = int(math.Floor((lat - g.minLat) / wayGridCellDegrees))
	col = int(math.Floor((lon - g.minLon) / wayGridCellDegrees))
	return row, col, row >= 0 && col >= 0 && row < g.rows && col < g.cols
}

func (g *wayGrid) clampedCell(lat, lon float64) (int, int) {
	row := int(math.Floor((lat - g.minLat) / wayGridCellDegrees))
	col := int(math.Floor((lon - g.minLon) / wayGridCellDegrees))
	return min(max(row, 0), g.rows-1), min(max(col, 0), g.cols-1)
}

func buildWayGrid(tile m.Box, ways []m.Box) *wayGrid {
	minLat, minLon := tile.MinPos.Lat()-WayMatchMargin, tile.MinPos.Lon()-WayMatchMargin
	maxLat, maxLon := tile.MaxPos.Lat()+WayMatchMargin, tile.MaxPos.Lon()+WayMatchMargin
	rows := int(math.Ceil((maxLat-minLat)/wayGridCellDegrees)) + 1
	cols := int(math.Ceil((maxLon-minLon)/wayGridCellDegrees)) + 1
	if rows <= 0 || cols <= 0 || rows*cols > wayGridMaxCells || math.IsNaN(minLat) || math.IsNaN(minLon) {
		return nil
	}
	g := &wayGrid{minLat: minLat, minLon: minLon, rows: rows, cols: cols, cells: make([][]int32, rows*cols)}
	for i, box := range ways {
		if box.MinPos.Lat() > box.MaxPos.Lat() || box.MinPos.Lon() > box.MaxPos.Lon() {
			continue
		}
		r0, c0 := g.clampedCell(box.MinPos.Lat()-WayMatchMargin, box.MinPos.Lon()-WayMatchMargin)
		r1, c1 := g.clampedCell(box.MaxPos.Lat()+WayMatchMargin, box.MaxPos.Lon()+WayMatchMargin)
		for r := r0; r <= r1; r++ {
			for c := c0; c <= c1; c++ {
				g.cells[r*cols+c] = append(g.cells[r*cols+c], int32(i))
			}
		}
	}
	return g
}

func (o *Offline) buildWayIndexes() {
	count := o.Ways.Len()
	boxes := make([]m.Box, count)
	o.endpoints = make(map[m.Position][]int32)
	for i := range count {
		raw := o.waysRaw.At(i)
		boxes[i] = m.Box{MinPos: m.NewPosition(raw.MinLat(), raw.MinLon()), MaxPos: m.NewPosition(raw.MaxLat(), raw.MaxLon())}
		nodes, err := raw.Nodes()
		if err != nil || nodes.Len() < 2 {
			continue
		}
		firstNode, lastNode := nodes.At(0), nodes.At(nodes.Len()-1)
		first := m.NewPosition(firstNode.Latitude(), firstNode.Longitude())
		last := m.NewPosition(lastNode.Latitude(), lastNode.Longitude())
		o.endpoints[first] = append(o.endpoints[first], int32(i))
		if !last.Equals(first) {
			o.endpoints[last] = append(o.endpoints[last], int32(i))
		}
	}
	o.grid = buildWayGrid(o.Box(), boxes)
}

// WaysNear returns the indices, in tile order, of every way whose padded box
// may contain pos. ok is false when the tile has no usable grid; callers then
// fall back to scanning every way.
func (o *Offline) WaysNear(pos m.Position) (indices []int32, ok bool) {
	row, col, inside := o.grid.cell(pos.Lat(), pos.Lon())
	if !inside {
		return nil, false
	}
	return o.grid.cells[row*o.grid.cols+col], true
}

// WaysWithEndpoint returns the indices, in tile order, of ways that start or
// end exactly at pos. ok is false when the tile has no index.
func (o *Offline) WaysWithEndpoint(pos m.Position) (indices []int32, ok bool) {
	if o.endpoints == nil {
		return nil, false
	}
	return o.endpoints[pos], true
}
