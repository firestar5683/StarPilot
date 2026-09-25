package main

import (
	"math"

	"pfeifer.dev/mapd/cereal/log"
	ms "pfeifer.dev/mapd/settings"
)

func calcVisionCurveSpeed(model log.ModelDataV2, state *State) float32 {
	xyztData, err := model.OrientationRate()
	if err != nil {
		return 0
	}
	zOrientRate, err := xyztData.Z()
	if err != nil {
		return 0
	}

	xyztData, err = model.Velocity()
	if err != nil {
		return 0
	}
	xVelocity, err := xyztData.X()
	if err != nil {
		return 0
	}

	predictedLatAccels := make([]float32, zOrientRate.Len())
	maxLatA := float32(0)
	vEgo := state.Car.VEgo
	if vEgo < 0.1 {
		vEgo = 0.1
	}

	for i := range zOrientRate.Len() {
		predictedLatAccels[i] = float32(math.Abs(float64(zOrientRate.At(i) * xVelocity.At(i))))
		if predictedLatAccels[i] > maxLatA {
			maxLatA = predictedLatAccels[i]
		}
	}

	maxCurve := maxLatA / (vEgo * vEgo)
	personality := ms.Settings.CurrentPersonality()
	vTarget := float32(math.Sqrt(float64(personality.VisionCurveTargetLatA / maxCurve)))
	if vTarget < personality.VisionCurveMinTargetV {
		vTarget = personality.VisionCurveMinTargetV
	}

	if vTarget < 0 {
		vTarget = 0
	} else if vTarget > 90*ms.MPH_TO_MS {
		vTarget = 90 * ms.MPH_TO_MS
	}
	vTarget = float32(state.VisionCurveMA.Update(float64(vTarget)))
	return vTarget
}
