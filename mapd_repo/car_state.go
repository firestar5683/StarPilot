package main

import (
	"time"

	"pfeifer.dev/mapd/cereal/car"
	m "pfeifer.dev/mapd/math"
	ms "pfeifer.dev/mapd/settings"
	"pfeifer.dev/mapd/utils"
)

type CarState struct {
	SetSpeed          utils.Float32Tracker
	VEgo              float32
	AEgo              float32
	VCruise           float32
	GasPressed        bool
	UpdateTime        utils.UpdateTracker
	SetSpeedChanging  bool
	EnableSpeedActive bool
}

func (c *CarState) Update(carData car.CarState) {
	c.SetSpeed.Update(carData.VCruise() * ms.KPH_TO_MS)
	c.VEgo = carData.VEgo()
	c.AEgo = carData.AEgo()
	c.VCruise = carData.VCruise()
	c.GasPressed = carData.GasPressed()
	c.SetSpeedChanging = time.Since(c.SetSpeed.UpdatedTime) < 1500*time.Millisecond
	if ms.Settings.EnableSpeed == 0 {
		c.EnableSpeedActive = true
	} else {
		c.EnableSpeedActive = m.Abs(c.SetSpeed.Value-ms.Settings.EnableSpeed) < ms.ENABLE_SPEED_RANGE
	}
	c.UpdateTime.Update()
}

func (c *CarState) Init() {
	c.SetSpeed.AllowNullLastValue = true
	c.UpdateTime.Init(100)
}
