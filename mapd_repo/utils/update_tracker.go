package utils

import (
	"time"

	m "pfeifer.dev/mapd/math"
)

type UpdateTracker struct {
	LastTime time.Time
	Time     time.Time
	DiffMA   m.MovingAverage
}

func (u *UpdateTracker) Init(maLength int) {
	u.LastTime = time.Now()
	u.Time = time.Now()
	u.DiffMA.Init(maLength)
}

func (u *UpdateTracker) Update() {
	u.LastTime = u.Time
	u.Time = time.Now()
	u.DiffMA.Update(u.Time.Sub(u.LastTime).Seconds())
}
