package cereal

import (
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
)

func MapdInCreator(evt log.Event) (custom.MapdIn, error) {
	return evt.NewMapdIn()
}

func MapdOutCreator(evt log.Event) (custom.MapdOut, error) {
	return evt.NewMapdOut()
}

func MapdExtendedOutCreator(evt log.Event) (custom.MapdExtendedOut, error) {
	return evt.NewMapdExtendedOut()
}
