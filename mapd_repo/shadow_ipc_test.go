package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"capnproto.org/go/capnp/v3"
	"github.com/pfeiferj/gomsgq"
	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/maps"
	ms "pfeifer.dev/mapd/settings"
)

// This test uses the production Go pump/publisher and actual IPC. Python's
// Galaxy MapStatus consumes the same bytes; no mapd executable is started.
func TestShadowGoPythonIPC(t *testing.T) {
	if os.Getenv("STARPILOT_SHADOW_IPC_REQUIRED") != "1" {
		t.Skip("cross-language IPC runs in the required host integration target")
	}
	python := os.Getenv("STARPILOT_PYTHON")
	if python == "" || !filepath.IsAbs(python) {
		t.Fatal("STARPILOT_PYTHON must name an absolute host Python with capnp/msgq")
	}
	if _, err := os.Stat(python); err != nil {
		t.Fatalf("required host Python is unavailable: %v", err)
	}
	priorPrefix := gomsgq.OPENPILOT_PREFIX
	priorMsgqPrefix := gomsgq.USE_MSGQ_PREFIX
	priorSettings := ms.Settings
	priorQueueSize := ms.ServiceQueueSize["mapdOut"]
	defer func() {
		gomsgq.OPENPILOT_PREFIX = priorPrefix
		gomsgq.USE_MSGQ_PREFIX = priorMsgqPrefix
		ms.Settings = priorSettings
		ms.ServiceQueueSize["mapdOut"] = priorQueueSize
	}()
	prefix := fmt.Sprintf("mapshadow_%d_%d", os.Getpid(), time.Now().UnixNano())
	base := "/tmp"
	if _, err := os.Stat("/dev/shm"); err == nil {
		base = "/dev/shm"
	}
	queueDir := filepath.Join(base, "msgq_"+prefix)
	if err := os.Mkdir(queueDir, 0700); err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(queueDir)
	t.Setenv("OPENPILOT_PREFIX", prefix)
	t.Setenv("USE_MSGQ_PREFIX", "false") // production initializer must override it
	initShadowIPC()
	if !gomsgq.IsPrefixedMsgq() || gomsgq.OPENPILOT_PREFIX != prefix || ms.GetSegmentSize("mapdOut") != ms.QUEUE_SIZE_SMALL {
		t.Fatal("shadow IPC does not match host queue path/size")
	}
	if err := initShadowDefaults(); err != nil {
		t.Fatal(err)
	}
	pub := cereal.NewPublisher("mapdOut", cereal.MapdOutCreator)
	defer pub.Pub.Msgq.Close()

	const script = `import json, os, sys
from openpilot.starpilot.galaxy.map_status import MapStatus
now = int(os.environ['SHADOW_TEST_BOOT'])
source = MapStatus(clock=lambda: now)
source.snapshot()  # subscribe before Go publishes
print('READY', flush=True)
for line in sys.stdin:
    if line.startswith('READ '):
        now = int(line.split()[1])
        print(json.dumps(source.snapshot()), flush=True)
    elif line.strip() == 'QUIT':
        break
source.close()
`
	boot := cereal.GetTime()
	cmdCtx, stop := context.WithTimeout(context.Background(), 10*time.Second)
	defer stop()
	cmd := exec.CommandContext(cmdCtx, python, "-u", "-c", script)
	cmd.Dir = ".."
	cmd.Env = append(os.Environ(), "OPENPILOT_PREFIX="+prefix, fmt.Sprintf("SHADOW_TEST_BOOT=%d", boot))
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	var stderr lockedIPCOutput
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() {
		fmt.Fprintln(stdin, "QUIT")
		stdin.Close()
		if err := cmd.Wait(); err != nil {
			t.Errorf("Python IPC consumer: %v: %s", err, stderr.String())
		}
	}()
	reader := bufio.NewReader(stdout)
	ready, err := reader.ReadString('\n')
	if err != nil || strings.TrimSpace(ready) != "READY" {
		t.Fatalf("Python subscriber failed: %q %v %s", ready, err, stderr.String())
	}

	state := State{ShadowOnly: true}
	state.Init()
	state.bootNow = func() uint64 { return boot }
	root := t.TempDir()
	id, err := maps.AdmitSnapshot(context.Background(), maps.AdmitOptions{Root: root, Bounds: [4]float64{35, -98, 35.25, -97.75}, Overlap: .001,
		PBF: filepath.Join("testdata", "synthetic_snapshot.osm.pbf"), SourceRevision: "test", UpstreamRevision: "test", SourceDigest: "test"})
	if err != nil {
		t.Fatal(err)
	}
	selected, receipt, err := maps.ResolveSnapshot(root)
	if err != nil || filepath.Base(selected) != id {
		t.Fatalf("snapshot selection: %v", err)
	}
	state.SnapshotID = id
	load := maps.SnapshotLoader(selected, receipt)
	sample := syntheticSample(t, cereal.GpsSourceExternal, boot-100_000_000, 1, true, true)
	ticks := make(chan time.Time)
	published := make(chan []byte, 2)
	loopCtx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan struct{})
	go func() {
		defer close(done)
		runShadowLoop(loopCtx, ticks, &state, func() (cereal.GpsSample, bool) { return sample, true },
			load, func(msg *capnp.Message) error {
				raw, err := msg.Marshal()
				if err != nil {
					return err
				}
				if err := pub.Send(msg); err != nil {
					return err
				}
				published <- raw
				return nil
			})
	}()
	for index := 0; index < 2; index++ {
		if index == 1 {
			// Valid but unrelated service packets cannot reach the GPS-only pump.
			for _, service := range []string{"carState", "modelV2", "selfdriveState", "mapdIn"} {
				publishIgnoredService(t, service)
			}
			boot += 50_000_000
			sample.NewFix, sample.SourceChanged = false, false
		}
		ticks <- time.Unix(0, int64(index))
		raw := <-published
		decoded, err := capnp.Unmarshal(raw)
		if err != nil {
			t.Fatal(err)
		}
		event, err := log.ReadRootEvent(decoded)
		if err != nil {
			t.Fatal(err)
		}
		out, err := event.MapdOut()
		if err != nil {
			t.Fatal(err)
		}
		if !event.Valid() || math.Abs(float64(out.SpeedLimit()-13.4112)) > .01 || out.SuggestedSpeed() != 0 || out.SpeedLimitAccepted() || out.NextSpeedLimit() != 0 || out.VisionCurveSpeed() != 0 || out.MapCurveSpeed() != 0 {
			t.Fatalf("Go shadow packet %d contaminated by control inputs", index)
		}
		if ms.Settings.SpeedLimitControlEnabled || state.Car.VEgo != 0 || state.VisionCurveSpeed != 0 || len(state.NextWays) != 0 {
			t.Fatalf("ignored source messages changed shadow state on tick %d", index)
		}
		fmt.Fprintf(stdin, "READ %d\n", boot)
		line, err := reader.ReadString('\n')
		if err != nil {
			t.Fatalf("Python status read: %v: %s", err, stderr.String())
		}
		var status struct {
			State     string  `json:"state"`
			Candidate float64 `json:"candidateSpeedMps"`
			Road      string  `json:"roadStatus"`
		}
		if err := json.Unmarshal([]byte(line), &status); err != nil {
			t.Fatal(err)
		}
		if status.State != "matched_limit_unqualified" || math.Abs(status.Candidate-13.4112) > .01 || status.Road != "matchedLimit" {
			t.Fatalf("Go-to-Python IPC observation %d: %s", index, line)
		}
	}
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("shadow loop did not close")
	}
}

func publishIgnoredService(t *testing.T, service string) {
	t.Helper()
	msg, seg, err := capnp.NewMessage(capnp.SingleSegment(nil))
	if err != nil {
		t.Fatal(err)
	}
	event, err := log.NewRootEvent(seg)
	if err != nil {
		t.Fatal(err)
	}
	event.SetValid(true)
	switch service {
	case "carState":
		car, createErr := event.NewCarState()
		err = createErr
		if err == nil {
			car.SetVEgo(32)
		}
	case "modelV2":
		model, createErr := event.NewModelV2()
		err = createErr
		if err == nil {
			model.SetFrameId(12345)
		}
	case "selfdriveState":
		selfdrive, createErr := event.NewSelfdriveState()
		err = createErr
		if err == nil {
			selfdrive.SetPersonality(log.LongitudinalPersonality_relaxed)
		}
	case "mapdIn":
		input, createErr := event.NewMapdIn()
		err = createErr
		if err == nil {
			input.SetType(custom.MapdInputType_setSpeedLimitControl)
			input.SetBool(true)
		}
	}
	if err != nil {
		t.Fatal(err)
	}
	raw, err := msg.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	queue := gomsgq.Msgq{}
	if err := queue.Init(service, ms.GetSegmentSize(service)); err != nil {
		t.Fatal(err)
	}
	publisher := gomsgq.MsgqPublisher{}
	publisher.Init(queue)
	publisher.Send(raw)
	queue.Close()
}

type lockedIPCOutput struct {
	mu    sync.Mutex
	value strings.Builder
}

func (b *lockedIPCOutput) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.value.Write(p)
}
func (b *lockedIPCOutput) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.value.String()
}
