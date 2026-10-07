package cereal

import (
	"capnproto.org/go/capnp/v3"
	"encoding/base64"
	"encoding/json"
	"os"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"testing"
)

func carGpsWire(t *testing.T, source, envelope uint64, valid, fix bool) []byte {
	t.Helper()
	message, segment, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.NewRootEvent(segment)
	if err != nil {
		t.Fatal(err)
	}
	event.SetLogMonoTime(envelope)
	event.SetValid(valid)
	state, err := event.NewStarpilotCarState()
	if err != nil {
		t.Fatal(err)
	}
	gps, err := state.NewGps()
	if err != nil {
		t.Fatal(err)
	}
	gps.SetSourceMonoTime(source)
	gps.SetHasFix(fix)
	gps.SetLatitude(40)
	gps.SetLongitude(-90)
	gps.SetAltitude(100)
	gps.SetSpeed(12)
	gps.SetBearingDeg(90)
	gps.SetHorizontalAccuracy(10)
	gps.SetVerticalAccuracy(10)
	gps.SetBearingAccuracyDeg(180)
	gps.SetSpeedAccuracy(1)
	gps.SetUnixTimestampMillis(123456)
	velocity, err := gps.NewVNED(3)
	if err != nil {
		t.Fatal(err)
	}
	velocity.Set(0, 12)
	raw, err := message.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func attachCar(s *GpsSub) *[][]byte {
	queue := [][]byte{}
	s.carGps = &Subscriber[custom.StarPilotCarState_Gps]{reader: CarGpsReader, maxBytes: 250 * 1024, readBytes: func() []byte {
		if len(queue) == 0 {
			return nil
		}
		value := queue[0]
		queue = queue[1:]
		return value
	}}
	return &queue
}

func TestCarGpsWireFallbackPriorityAndOriginalAge(t *testing.T) {
	now := uint64(10_000_000_000)
	s, internal, external := testGpsSub(&now)
	car := attachCar(s)
	source := now - 100_000_000
	*car = append(*car, carGpsWire(t, source, now, true, true))
	sample, ok := s.ReadSample()
	if !ok || sample.Source != GpsSourceCar || sample.FixMonoTime != source || !sample.NewFix || sample.Location.Source() != log.GpsLocationData_SensorSource_car || sample.Location.UnixTimestampMillis() != 123456 || sample.Location.BearingAccuracyDeg() != 180 {
		t.Fatalf("car wire: %+v %v", sample, ok)
	}
	velocity, err := sample.Location.VNED()
	if err != nil || velocity.Len() != 3 || velocity.At(0) != 12 {
		t.Fatal("velocity conversion", err)
	}
	now += 100_000_000
	*car = append(*car, carGpsWire(t, source, now, true, true))
	sample, ok = s.ReadSample()
	if !ok || sample.NewFix || sample.FixMonoTime != source {
		t.Fatal("envelope renewed source")
	}
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now, true, true, 1, 2, 5))
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceInternal {
		t.Fatal("internal priority")
	}
	*external = append(*external, gpsWire(t, GpsSourceExternal, now, true, true, 3, 4, 5))
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceExternal {
		t.Fatal("external priority")
	}
	now = source + carFixMaxAge
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceCar {
		t.Fatal("fallback TTL boundary")
	}
	now++
	*car = append(*car, carGpsWire(t, source, now, true, true))
	if _, ok = s.ReadSample(); ok {
		t.Fatal("expired source rejuvenated")
	}
}

func TestCarGpsClockAndInvalidFix(t *testing.T) {
	now := uint64(10_000_000_000)
	s, _, _ := testGpsSub(&now)
	queue := attachCar(s)
	for _, stamps := range [][2]uint64{{0, now}, {now + 1, now}, {now, now + 1}, {now - carFixMaxAge - 1, now}} {
		*queue = append(*queue, carGpsWire(t, stamps[0], stamps[1], true, true))
		if _, ok := s.ReadSample(); ok {
			t.Fatal("invalid timestamp admitted", stamps)
		}
	}
	*queue = append(*queue, carGpsWire(t, now, now, true, true))
	if _, ok := s.ReadSample(); !ok {
		t.Fatal("fresh fix")
	}
	now++
	*queue = append(*queue, carGpsWire(t, now, now, false, true))
	if _, ok := s.ReadSample(); ok {
		t.Fatal("invalid fix retained")
	}
	now++
	*queue = append(*queue, carGpsWire(t, now, now, true, false))
	if _, ok := s.ReadSample(); ok {
		t.Fatal("no-fix admitted")
	}
	now++
	*queue = append(*queue, carGpsWire(t, now, now, true, true))
	if _, ok := s.ReadSample(); !ok {
		t.Fatal("fresh recovery")
	}
	s.clock = func() clockSample { return clockSample{now, now + 1_000_000_000, now} }
	if _, ok := s.ReadSample(); ok {
		t.Fatal("suspend did not fence car")
	}
	*queue = append(*queue, carGpsWire(t, now, now, true, true))
	if _, ok := s.ReadSample(); ok {
		t.Fatal("pre-resume source accepted")
	}
	now++
	*queue = append(*queue, carGpsWire(t, now, now, true, true))
	if _, ok := s.ReadSample(); !ok {
		t.Fatal("post-resume fix denied")
	}
}

func TestOptionalCarGpsAbsentPreservesHardware(t *testing.T) {
	now := uint64(10_000_000_000)
	s, _, external := testGpsSub(&now)
	*external = append(*external, gpsWire(t, GpsSourceExternal, now, true, true, 1, 2, 5))
	if sample, ok := s.ReadSample(); !ok || sample.Source != GpsSourceExternal {
		t.Fatal("absent optional source disturbed hardware")
	}
}

func TestPythonStarPilotCarGpsWire(t *testing.T) {
	raw, err := os.ReadFile("testdata/car_gps_python_wire.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		DataBase64     string
		SourceMonoTime uint64
		EventMonoTime  uint64
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	wire, err := base64.StdEncoding.DecodeString(fixture.DataBase64)
	if err != nil {
		t.Fatal(err)
	}
	now := fixture.EventMonoTime
	s, _, _ := testGpsSub(&now)
	queue := attachCar(s)
	*queue = append(*queue, wire)
	sample, ok := s.ReadSample()
	if !ok || sample.Source != GpsSourceCar || sample.FixMonoTime != fixture.SourceMonoTime || sample.Location.Latitude() != 40 || sample.Location.Longitude() != -90 || sample.Location.Speed() != 12 || sample.Location.BearingDeg() != 90 || sample.Location.HorizontalAccuracy() != 10 || sample.Location.BearingAccuracyDeg() != 180 || sample.Location.UnixTimestampMillis() != 123456 {
		t.Fatalf("Python wire decoded incorrectly: %+v %v", sample, ok)
	}
	velocity, err := sample.Location.VNED()
	if err != nil || velocity.Len() != 3 || velocity.At(0) != 12 || velocity.At(1) != 0 || velocity.At(2) != 0 {
		t.Fatal("Python NED", err)
	}
	now = fixture.SourceMonoTime + carFixMaxAge + 1
	*queue = append(*queue, wire)
	if _, ok = s.ReadSample(); ok {
		t.Fatal("Python source expired but republish renewed")
	}
}
