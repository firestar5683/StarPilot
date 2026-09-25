package math

import "math"

func Abs[T float64 | float32](val T) float64 {
	return math.Abs(float64(val))
}
