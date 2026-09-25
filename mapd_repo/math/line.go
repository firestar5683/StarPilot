package math

type Line struct {
	Start, End Position
}

type LinePosition struct {
	Pos Position
	T   float64
}

func (l *Line) NearestPosition(pos Position) LinePosition {
	AB := l.End.Subtract(l.Start)
	AP := pos.Subtract(l.Start)
	t := AP.Dot(AB) / AB.Dot(AB)

	t = max(0, min(1, t))
	closest := l.Start.Add(AB.Scale(t))
	return LinePosition{Pos: closest, T: t}
}
