package math

import (
	m "math"
)

type Curvature struct {
	Curvature, ArcLength, Angle float64
	Pos                         Position
}

func CalculateCurvature(a Position, b Position, c Position) Curvature {
	lengthA := a.DistanceTo(b)
	lengthB := a.DistanceTo(c)
	lengthC := b.DistanceTo(c)

	sp := (lengthA + lengthB + lengthC) / 2

	area := float32(m.Sqrt(float64(sp * (sp - lengthA) * (sp - lengthB) * (sp - lengthC))))

	lengthProd := lengthA * lengthB * lengthC
	if lengthProd == 0 {
		return Curvature{Pos: b}
	}

	res := Curvature{Pos: b}
	res.Curvature = float64((4 * area) / lengthProd)
	radius := 1.0 / res.Curvature

	num := (m.Pow(radius, 2)*2 - m.Pow(float64(lengthB), 2))
	den := (2 * m.Pow(radius, 2))
	res.Angle = m.Acos(num / den)

	res.ArcLength = radius * res.Angle

	return res
}
