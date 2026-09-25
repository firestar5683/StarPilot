package cereal

import (
	"pfeifer.dev/mapd/cereal/car"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
)

func MapdInReader(evt log.Event) (custom.MapdIn, error) {
	return evt.MapdIn()
}

func MapdOutReader(evt log.Event) (custom.MapdOut, error) {
	return evt.MapdOut()
}

func MapdExtendedOutReader(evt log.Event) (custom.MapdExtendedOut, error) {
	return evt.MapdExtendedOut()
}

func CarStateReader(evt log.Event) (car.CarState, error) {
	return evt.CarState()
}

func ModelV2Reader(evt log.Event) (log.ModelDataV2, error) {
	return evt.ModelV2()
}

func GpsLocationReader(evt log.Event) (log.GpsLocationData, error) {
	return evt.GpsLocation()
}

func GpsLocationExternalReader(evt log.Event) (log.GpsLocationData, error) {
	return evt.GpsLocationExternal()
}

func SelfdriveStateReader(evt log.Event) (log.SelfdriveState, error) {
	return evt.SelfdriveState()
}
