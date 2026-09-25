package math

import (
	m "math"
)

type Vector struct {
	X float64
	Y float64
}

func (v *Vector) Bearing() float64 {
	return m.Atan2(v.X, v.Y)
}
