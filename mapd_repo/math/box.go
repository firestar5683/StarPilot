package math

import (
	"math"

	ms "pfeifer.dev/mapd/settings"
)

type Box struct {
	MinPos Position
	MaxPos Position
}

func (b *Box) PosInside(p Position) bool {
	return p.Lat() >= b.MinPos.Lat() && p.Lat() <= b.MaxPos.Lat() && p.Lon() >= b.MinPos.Lon() && p.Lon() <= b.MaxPos.Lon()
}

func (b *Box) GroupPos() Position {
	group_lat_directory := math.Floor(b.MinPos.Lat()/float64(ms.GROUP_AREA_BOX_DEGREES)) * ms.GROUP_AREA_BOX_DEGREES
	group_lon_directory := math.Floor(b.MinPos.Lon()/float64(ms.GROUP_AREA_BOX_DEGREES)) * ms.GROUP_AREA_BOX_DEGREES
	return NewPosition(group_lat_directory, group_lon_directory)
}

func (b *Box) AreaPos() Position {
	area_lat_directory := math.Floor(b.MinPos.Lat()/float64(ms.AREA_BOX_DEGREES)) * ms.AREA_BOX_DEGREES
	area_lon_directory := math.Floor(b.MinPos.Lon()/float64(ms.AREA_BOX_DEGREES)) * ms.AREA_BOX_DEGREES
	return NewPosition(area_lat_directory, area_lon_directory)
}

func (a *Box) Overlapping(b Box) bool {
	intersect := !(a.MinPos.Lat() > b.MaxPos.Lat() ||
		a.MaxPos.Lat() < b.MinPos.Lat() ||
		a.MinPos.Lon() > b.MaxPos.Lon() ||
		a.MaxPos.Lon() < b.MinPos.Lon())
	aMinInside := b.PosInside(a.MinPos)
	bMinInside := a.PosInside(b.MinPos)
	aMaxInside := b.PosInside(a.MaxPos)
	bMaxInside := a.PosInside(b.MaxPos)
	return intersect || aMinInside || bMinInside || aMaxInside || bMaxInside
}

func (a *Box) Contains(b Box) bool {
	bMinInside := a.PosInside(b.MinPos)
	bMaxInside := a.PosInside(b.MaxPos)
	return bMinInside && bMaxInside
}

func (a *Box) Equals(b Box) bool {
	return a.MinPos.Equals(b.MinPos) && a.MaxPos.Equals(b.MaxPos)
}

func (b *Box) Overlap(overlap float64) Box {
	return Box{
		MinPos: NewPosition(b.MinPos.Lat()-overlap, b.MinPos.Lon()-overlap),
		MaxPos: NewPosition(b.MaxPos.Lat()+overlap, b.MaxPos.Lon()+overlap),
	}
}
