package math

import (
	m "math"

	"pfeifer.dev/mapd/cereal/log"
	ms "pfeifer.dev/mapd/settings"
)

func NewPosition(latDeg, lonDeg float64) Position {
	return Position{latitudeDeg: latDeg, longitudeDeg: lonDeg}
}

func PosFromLocation(loc log.GpsLocationData) Position {
	return Position{latitudeDeg: loc.Latitude(), longitudeDeg: loc.Longitude()}
}

type Position struct {
	latitudeDeg  float64
	longitudeDeg float64
}

func (p *Position) LatRad() float64 {
	return p.latitudeDeg * ms.TO_RADIANS
}

func (p *Position) LonRad() float64 {
	return p.longitudeDeg * ms.TO_RADIANS
}

func (p *Position) Lat() float64 {
	return p.latitudeDeg
}

func (p *Position) Lon() float64 {
	return p.longitudeDeg
}

func (p *Position) DistanceTo(end Position) float32 {
	latDiff := end.LatRad() - p.LatRad()
	lonDiff := end.LonRad() - p.LonRad()
	a := m.Pow(m.Sin(latDiff/2), 2) + m.Cos(p.LatRad())*m.Cos(end.LatRad())*m.Pow(m.Sin(lonDiff/2), 2)
	c := 2 * m.Atan2(m.Sqrt(a), m.Sqrt(1-a))

	return float32(ms.R * c) // in metres
}

func (p *Position) Subtract(other Position) Position {
	return Position{latitudeDeg: p.Lat() - other.Lat(), longitudeDeg: p.Lon() - other.Lon()}
}

func (p *Position) Add(other Position) Position {
	return Position{latitudeDeg: p.Lat() + other.Lat(), longitudeDeg: p.Lon() + other.Lon()}
}

func (p *Position) Scale(factor float64) Position {
	return Position{latitudeDeg: p.Lat() * factor, longitudeDeg: p.Lon() * factor}
}

func (p *Position) Dot(other Position) float64 {
	return p.Lat()*other.Lat() + p.Lon()*other.Lon()
}

func (p *Position) Equals(other Position) bool {
	return p.Lat() == other.Lat() && p.Lon() == other.Lon()
}

func (p *Position) VectorTo(end Position) Vector {
	res := Vector{}
	dlon := end.LonRad() - p.LonRad()
	res.X = m.Sin(dlon) * m.Cos(end.LatRad())
	res.Y = m.Cos(p.LatRad())*m.Sin(end.LatRad()) - (m.Sin(p.LatRad()) * m.Cos(end.LatRad()) * m.Cos(dlon))
	return res
}
