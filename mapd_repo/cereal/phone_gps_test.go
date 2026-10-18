package cereal

import (
	"capnproto.org/go/capnp/v3"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"testing"
)

func phoneGpsWire(t *testing.T, source, envelope uint64) []byte {
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
	event.SetValid(true)
	phone, err := event.NewPhoneGps()
	if err != nil {
		t.Fatal(err)
	}
	gps, err := phone.NewGps()
	if err != nil {
		t.Fatal(err)
	}
	gps.SetSourceMonoTime(source)
	gps.SetHasFix(true)
	gps.SetLatitude(41)
	gps.SetLongitude(-111)
	gps.SetAltitude(100)
	gps.SetSpeed(12)
	gps.SetBearingDeg(90)
	gps.SetHorizontalAccuracy(5)
	gps.SetVerticalAccuracy(5)
	gps.SetBearingAccuracyDeg(10)
	gps.SetSpeedAccuracy(1)
	raw, err := message.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func attachPhone(s *GpsSub, mode *string) *[][]byte {
	queue := [][]byte{}
	s.phoneGps = &Subscriber[custom.StarPilotCarState_Gps]{reader: PhoneGpsReader, maxBytes: 250 * 1024, readBytes: func() []byte {
		if len(queue) == 0 {
			return nil
		}
		value := queue[0]
		queue = queue[1:]
		return value
	}}
	s.mode = func() string { return *mode }
	return &queue
}

func TestPhoneGpsFollowsTheGalaxySetting(t *testing.T) {
	now := uint64(10_000_000_000)
	mode := GpsModeBackup
	s, internal, _ := testGpsSub(&now)
	car := attachCar(s)
	phone := attachPhone(s, &mode)

	*phone = append(*phone, phoneGpsWire(t, now-300_000_000, now))
	sample, ok := s.ReadSample()
	if !ok || sample.Source != GpsSourcePhone || sample.FixMonoTime != now-300_000_000 || sample.Location.Longitude() != -111 {
		t.Fatalf("backup without comma or car GPS: %+v %v", sample, ok)
	}
	*car = append(*car, carGpsWire(t, now-1, now, true, true))
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceCar {
		t.Fatal("car ranks above the phone in backup")
	}
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now, true, true, 1, 2, 5))
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceInternal {
		t.Fatal("comma ranks above the phone in backup")
	}

	mode = GpsModePhone
	now += gpsModeRefresh
	*phone = append(*phone, phoneGpsWire(t, now-100_000_000, now))
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now, true, true, 1, 2, 5))
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourcePhone {
		t.Fatal("prefer phone")
	}
	now += phoneFixMaxAge
	*internal = append(*internal, gpsWire(t, GpsSourceInternal, now, true, true, 1, 2, 5))
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceInternal {
		t.Fatal("prefer phone falls back to comma once the phone fix expires")
	}

	mode = GpsModeComma
	now += gpsModeRefresh
	*phone = append(*phone, phoneGpsWire(t, now, now))
	if sample, ok = s.ReadSample(); !ok || sample.Source != GpsSourceInternal {
		t.Fatal("comma and car only keeps comma GPS")
	}
	now += internalFixMaxAge + 1
	*phone = append(*phone, phoneGpsWire(t, now, now))
	if _, ok = s.ReadSample(); ok {
		t.Fatal("comma and car only must never use the phone")
	}
}

func TestPhoneGpsModeIsRereadAtMostOnceASecond(t *testing.T) {
	now := uint64(10_000_000_000)
	reads := 0
	s, _, _ := testGpsSub(&now)
	s.mode = func() string { reads++; return GpsModeBackup }
	s.ReadSample()
	now += gpsModeRefresh - 1
	s.ReadSample()
	if reads != 1 {
		t.Fatalf("mode reread early: %d", reads)
	}
	now++
	s.ReadSample()
	if reads != 2 {
		t.Fatalf("mode not reread: %d", reads)
	}
}
