package cereal

import (
	"bytes"
	"capnproto.org/go/capnp/v3"
	"encoding/base64"
	"encoding/json"
	"os"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"testing"
)

func TestMapdIOProviderWireFixture(t *testing.T) {
	check := func(err error) {
		t.Helper()
		if err != nil {
			t.Fatal(err)
		}
	}
	output := map[string]string{}
	for _, name := range []string{"extended", "input"} {
		msg, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
		check(err)
		event, err := log.NewRootEvent(seg)
		check(err)
		event.SetLogMonoTime(780000000000)
		event.SetValid(true)
		if name == "extended" {
			out, err := event.NewMapdExtendedOut()
			check(err)
			progress, err := out.NewDownloadProgress()
			check(err)
			progress.SetActive(true)
			progress.SetCancelled(false)
			progress.SetTotalFiles(10)
			progress.SetDownloadedFiles(4)
			locations, err := progress.NewLocations(1)
			check(err)
			check(locations.Set(0, "synthetic-region"))
			details, err := progress.NewLocationDetails(1)
			check(err)
			detail := details.At(0)
			check(detail.SetLocation("synthetic-region"))
			detail.SetTotalFiles(10)
			detail.SetDownloadedFiles(4)
			check(out.SetSettings("{\"fixture\":true}"))
			path, err := out.NewPath(1)
			check(err)
			point := path.At(0)
			point.SetLatitude(35.15)
			point.SetLongitude(-97.9)
			point.SetCurvature(0.001)
			point.SetTargetVelocity(12.5)
			pos, err := out.NewPosition()
			check(err)
			pos.SetLatitude(35.151)
			pos.SetLongitude(-97.901)
			out.SetLoopRateAverage(20)
			out.SetLoopRateMin(18.5)
		} else {
			in, err := event.NewMapdIn()
			check(err)
			in.SetType(custom.MapdInputType_setJsonPathFloat)
			in.SetFloat(2.75)
			check(in.SetStr("synthetic input"))
			in.SetBool(true)
			check(in.SetJsonPath("curve.targetLatA"))
		}
		raw, err := msg.Marshal()
		check(err)
		output[name+"_event_base64"] = base64.StdEncoding.EncodeToString(raw)
	}
	rawFixture, err := os.ReadFile("testdata/mapd_io_wire.json")
	check(err)
	var fixture struct {
		Provider map[string]string `json:"provider"`
	}
	check(json.Unmarshal(rawFixture, &fixture))
	for name, value := range output {
		if value != fixture.Provider[name] {
			t.Fatalf("provider %s changed; review host/schema wire compatibility", name)
		}
	}
}

func TestMapdIOHostInputReadsInProvider(t *testing.T) {
	rawFixture, err := os.ReadFile("testdata/mapd_io_wire.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Host map[string]string `json:"host"`
	}
	if err := json.Unmarshal(rawFixture, &fixture); err != nil {
		t.Fatal(err)
	}
	raw, err := base64.StdEncoding.DecodeString(fixture.Host["input_event_base64"])
	if err != nil {
		t.Fatal(err)
	}
	msg, err := capnp.NewDecoder(bytes.NewReader(raw)).Decode()
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.ReadRootEvent(msg)
	if err != nil {
		t.Fatal(err)
	}
	if event.Which() != log.Event_Which_mapdIn || !event.Valid() || event.LogMonoTime() != 790000000000 {
		t.Fatal("wrong host input envelope")
	}
	in, err := event.MapdIn()
	if err != nil {
		t.Fatal(err)
	}
	str, err := in.Str()
	if err != nil {
		t.Fatal(err)
	}
	path, err := in.JsonPath()
	if err != nil {
		t.Fatal(err)
	}
	if in.Type() != custom.MapdInputType_setJsonPathText || in.Float() != 1.5 || !in.Bool() || str != "host fixture" || path != "display.units" {
		t.Fatal("host input field meaning changed")
	}
}
