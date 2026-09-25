package utils

import (
	"math"
	"time"
)

type Float32Tracker struct {
	LastValue          float32
	Value              float32
	UpdatedTime        time.Time
	AllowNullLastValue bool
}

func (t *Float32Tracker) Update(val float32) (updated bool) {
	if t.Value != val {
		if t.AllowNullLastValue || !(math.IsNaN(float64(t.Value)) || t.Value == 0) {
			t.LastValue = t.Value
		}
		t.UpdatedTime = time.Now()
		t.Value = val
		return true
	}
	return false
}
