package cereal

import (
	"math"
	"testing"
	"time"

	"capnproto.org/go/capnp/v3"
	carcapnp "pfeifer.dev/mapd/cereal/car"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
)

func gpsWire(t *testing.T, source GpsSource, mono uint64, eventValid, hasFix bool, latitude, longitude float64, accuracy float32) []byte {
	t.Helper()
	msg, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.NewRootEvent(seg)
	if err != nil {
		t.Fatal(err)
	}
	event.SetLogMonoTime(mono)
	event.SetValid(eventValid)
	var gps log.GpsLocationData
	if source == GpsSourceExternal {
		gps, err = event.NewGpsLocationExternal()
	} else {
		gps, err = event.NewGpsLocation()
	}
	if err != nil {
		t.Fatal(err)
	}
	gps.SetHasFix(hasFix)
	gps.SetLatitude(latitude)
	gps.SetLongitude(longitude)
	gps.SetHorizontalAccuracy(accuracy)
	data, err := msg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func wireQueue(reader Reader[log.GpsLocationData]) (Subscriber[log.GpsLocationData], *[][]byte) {
	queue := new([][]byte)
	sub := Subscriber[log.GpsLocationData]{reader: reader, maxBytes: 250 * 1024}
	sub.readBytes = func() []byte {
		if len(*queue) == 0 {
			return nil
		}
		data := (*queue)[0]
		*queue = (*queue)[1:]
		return data
	}
	return sub, queue
}

func testGpsSub(now *uint64) (*GpsSub, *[][]byte, *[][]byte) {
	internal, internalQueue := wireQueue(GpsLocationReader)
	external, externalQueue := wireQueue(GpsLocationExternalReader)
	return &GpsSub{gpsLocation: internal, gpsLocationExternal: external,
		clock: func() clockSample { return clockSample{*now, *now, *now} }, clockInitialized: true}, internalQueue, externalQueue
}

func TestSubscriberEventMetadataAndCompatibility(t *testing.T) {
	sub, queue := wireQueue(GpsLocationReader)
	*queue = append(*queue, gpsWire(t, GpsSourceInternal, 123, false, true, 1, 2, 5))
	event, ok := sub.ReadEvent()
	if !ok || event.Valid || event.LogMonoTime != 123 || event.Value.Latitude() != 1 {
		t.Fatalf("metadata: %+v, %v", event, ok)
	}
	*queue = append(*queue, gpsWire(t, GpsSourceInternal, 124, false, true, 3, 4, 5))
	value, ok := sub.Read() // old callers retain value-only semantics
	if !ok || value.Latitude() != 3 {
		t.Fatal("value-only compatibility")
	}
	sub.maxBytes = 8
	*queue = append(*queue, gpsWire(t, GpsSourceInternal, 125, true, true, 1, 2, 5))
	if _, ok := sub.ReadEvent(); ok {
		t.Fatal("oversized event accepted")
	}
	sub.maxBytes = 250 * 1024
	*queue = append(*queue, []byte{1, 2, 3})
	if _, ok := sub.ReadEvent(); ok {
		t.Fatal("malformed event accepted")
	}
	*queue = append(*queue, gpsWire(t, GpsSourceExternal, 126, true, true, 1, 2, 5))
	if _, ok := sub.ReadEvent(); ok {
		t.Fatal("wrong event variant accepted")
	}
}

func TestCarAndModelValueOnlyReadersRemainCompatible(t *testing.T) {
	carMsg, carSeg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	carEvent, err := log.NewRootEvent(carSeg)
	if err != nil {
		t.Fatal(err)
	}
	carEvent.SetValid(false)
	car, err := carEvent.NewCarState()
	if err != nil {
		t.Fatal(err)
	}
	car.SetVEgo(12.5)
	carBytes, err := carMsg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	carSub := Subscriber[carcapnp.CarState]{reader: CarStateReader, maxBytes: 250 * 1024, readBytes: func() []byte { return carBytes }}
	carValue, ok := carSub.Read()
	if !ok || carValue.VEgo() != 12.5 {
		t.Fatal("car value-only read changed")
	}

	modelMsg, modelSeg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	modelEvent, err := log.NewRootEvent(modelSeg)
	if err != nil {
		t.Fatal(err)
	}
	model, err := modelEvent.NewModelV2()
	if err != nil {
		t.Fatal(err)
	}
	model.SetFrameId(17)
	if err := model.SetRawPredictions(make([]byte, 512*1024)); err != nil {
		t.Fatal(err)
	}
	modelBytes, err := modelMsg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	modelSub := Subscriber[log.ModelDataV2]{reader: ModelV2Reader, maxBytes: 10 * 1024 * 1024, readBytes: func() []byte { return modelBytes }}
	modelValue, ok := modelSub.Read()
	if !ok || modelValue.FrameId() != 17 {
		t.Fatal("large model value-only read changed")
	}
}

func TestGpsExternalFallbackRecoveryAndOriginalFixTime(t *testing.T) {
	now := uint64(10_000_000_000)
	s, internal, external := testGpsSub(&now)
	internalTime, externalTime := now-100_000_000, now-50_000_000
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, internalTime, true, true, 1, 2, 5))
	*external = append(*external, gpsWire(t, GpsSourceExternal, externalTime, true, true, 3, 4, 5))
	sample, ok := s.ReadSample()
	if !ok || sample.Source != GpsSourceExternal || sample.FixMonoTime != externalTime || !sample.NewFix || !sample.SourceChanged || sample.SourceGeneration != 1 {
		t.Fatalf("external priority: %+v %v", sample, ok)
	}
	now += 100_000_000
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceExternal || sample.FixMonoTime != externalTime || sample.NewFix || sample.SourceChanged {
		t.Fatalf("same fix reuse: %+v %v", sample, ok)
	}
	now = externalTime + externalFixMaxAge
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceExternal {
		t.Fatalf("external at TTL edge: %+v %v", sample, ok)
	}
	now++
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceInternal || sample.FixMonoTime != internalTime || !sample.SourceChanged || sample.SourceGeneration != 2 {
		t.Fatalf("fallback: %+v %v", sample, ok)
	}
	*external = append(*external, gpsWire(t, GpsSourceExternal, now, true, true, 5, 6, 5))
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceExternal || !sample.SourceChanged || sample.SourceGeneration != 3 {
		t.Fatalf("recovery: %+v %v", sample, ok)
	}
	*external = append(*external, gpsWire(t, GpsSourceExternal, now+1, false, true, 5, 6, 5))
	now++
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceInternal || !sample.SourceChanged || sample.SourceGeneration != 4 {
		t.Fatalf("fresh invalid external must fall back now: %+v %v", sample, ok)
	}
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now+1, true, false, 1, 2, 5))
	now++
	sample, ok = s.ReadSample()
	if ok || sample.Source != GpsSourceNone || !sample.SourceChanged || sample.SourceGeneration != 5 {
		t.Fatalf("fresh invalid internal must clear now: %+v %v", sample, ok)
	}
}

func TestGpsFreshnessValidationAndReplay(t *testing.T) {
	now := uint64(10_000_000_000)
	s, internal, external := testGpsSub(&now)
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now, true, true, 1, 2, 5))
	sample, ok := s.ReadSample()
	if !ok || sample.FixMonoTime != now {
		t.Fatal("initial fix")
	}
	// Neither an old invalid replay nor a future fix may overwrite the good fix.
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now-1, false, false, 1, 2, 5), gpsWire(t, GpsSourceInternal, now+1, true, true, 9, 9, 5))
	if sample, ok = s.ReadSample(); !ok || sample.FixMonoTime != now {
		t.Fatal("replay changed fix")
	}
	if sample, ok = s.ReadSample(); !ok || sample.FixMonoTime != now {
		t.Fatal("future fix accepted")
	}
	for _, bad := range []struct {
		lat, lon float64
		accuracy float32
		hasFix   bool
	}{
		{91, 2, 5, true}, {1, -181, 5, true}, {math.NaN(), 2, 5, true},
		{1, 2, 0, true}, {1, 2, 51, true}, {1, 2, float32(math.NaN()), true}, {1, 2, 5, false},
	} {
		now++
		*external = append(*external, gpsWire(t, GpsSourceExternal, now, true, bad.hasFix, bad.lat, bad.lon, bad.accuracy))
		if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceInternal {
			t.Fatalf("invalid external selected: %+v %v", sample, ok)
		}
	}
	now++
	badBearing := gpsWire(t, GpsSourceExternal, now, true, true, 1, 2, 5)
	bearingMsg, err := capnp.Unmarshal(badBearing)
	if err != nil {
		t.Fatal(err)
	}
	bearingEvent, err := log.ReadRootEvent(bearingMsg)
	if err != nil {
		t.Fatal(err)
	}
	bearingFix, err := bearingEvent.GpsLocationExternal()
	if err != nil {
		t.Fatal(err)
	}
	bearingFix.SetBearingDeg(float32(math.NaN()))
	badBearing, err = bearingMsg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	*external = append(*external, badBearing)
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceInternal {
		t.Fatalf("invalid bearing reached source selection: %+v %v", sample, ok)
	}
	now = sample.FixMonoTime + internalFixMaxAge
	if _, ok = s.ReadSample(); !ok {
		t.Fatal("internal exact TTL edge rejected")
	}
	now++
	if sample, ok = s.ReadSample(); ok || sample.Source != GpsSourceNone {
		t.Fatalf("expired fix reused: %+v %v", sample, ok)
	}
}

func TestPublisherDoesNotRebroadcastOrRetimestamp(t *testing.T) {
	var sent []uint64
	p := Publisher[custom.MapdOut]{creator: MapdOutCreator, msgChan: make(chan *capnp.Message, 1), stop: make(chan struct{}), done: make(chan struct{})}
	ticks := make(chan time.Time)
	tickDone := make(chan struct{})
	go p.runAutoPublishLoop(ticks, tickDone)
	defer func() { close(p.stop); <-p.done }()
	tick := func() { ticks <- time.Time{}; <-tickDone }
	p.sendMessage = func(msg *capnp.Message) error {
		event, err := log.ReadRootEvent(msg)
		if err != nil {
			return err
		}
		sent = append(sent, event.LogMonoTime())
		return nil
	}
	msg, _ := p.NewMessage(true)
	event, err := log.ReadRootEvent(msg)
	if err != nil {
		t.Fatal(err)
	}
	event.SetLogMonoTime(123)
	p.Publish(msg)
	tick()
	tick()
	if len(sent) != 1 || sent[0] != 123 || event.LogMonoTime() != 123 {
		t.Fatalf("stale rebroadcast/retimestamp: %v", sent)
	}
	msg1, _ := p.NewMessage(true)
	msg2, _ := p.NewMessage(true)
	event1, _ := log.ReadRootEvent(msg1)
	event2, _ := log.ReadRootEvent(msg2)
	event1.SetLogMonoTime(124)
	event2.SetLogMonoTime(125)
	p.Publish(msg1)
	p.Publish(msg2)
	tick()
	if len(sent) != 2 || sent[1] != 125 {
		t.Fatalf("newest queued sample not sent once: %v", sent)
	}
}
