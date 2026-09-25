package main

import (
	"context"
	"errors"
	"flag"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"capnproto.org/go/capnp/v3"
	"github.com/pfeiferj/gomsgq"

	"pfeifer.dev/mapd/cereal"
	"pfeifer.dev/mapd/cli"
	"pfeifer.dev/mapd/maps"
	ms "pfeifer.dev/mapd/settings"
)

func main() {
	logBuildInfo()
	if len(os.Args) > 1 && os.Args[1] == "--snapshot-admit" {
		if err := runSnapshotAdmit(os.Args[2:]); err != nil {
			slog.Error("offline snapshot admission failed", "error", err)
			os.Exit(2)
		}
		return
	}
	if len(os.Args) > 1 && os.Args[1] == "--snapshot-fetch" {
		if err := runSnapshotFetch(os.Args[2:]); err != nil {
			slog.Error("offline snapshot fetch failed", "error", err)
			os.Exit(2)
		}
		return
	}
	if len(os.Args) > 1 && os.Args[1] == "--snapshot-catalog" {
		if err := runSnapshotCatalog(os.Args[2:]); err != nil {
			slog.Error("snapshot catalog unavailable", "error", err)
			os.Exit(2)
		}
		return
	}
	if len(os.Args) > 1 && os.Args[1] == "--snapshot-managed-prepare" {
		if err := runSnapshotManagedPrepare(os.Args[2:]); err != nil {
			slog.Error("managed snapshot preparation failed", "error", err)
			os.Exit(2)
		}
		return
	}
	if len(os.Args) > 1 && os.Args[1] == "--snapshot-select" {
		if err := runSnapshotSelect(os.Args[2:]); err != nil {
			slog.Error("prepared snapshot selection failed", "error", err)
			os.Exit(2)
		}
		return
	}
	if len(os.Args) > 1 && os.Args[1] == "--shadow" {
		if err := runShadowArgs(os.Args[2:]); err != nil {
			slog.Error("shadow map observation unavailable", "error", err)
			os.Exit(2)
		}
		return
	}
	ms.Settings.Default()                // set defaults so settings not already in param are defaulted
	settingsLoaded := ms.Settings.Load() // try loading settings before cli

	cli.Handle()

	if !settingsLoaded {
		ms.Settings.LoadWithRetries(5)
	}

	state := State{}
	state.Init()

	extendedState := ExtendedState{
		Pub:   cereal.NewPublisher("mapdExtendedOut", cereal.MapdExtendedOutCreator),
		state: &state,
	}
	extendedState.Pub.StartAutoPublish(time.Second)
	defer extendedState.Pub.Stop()
	defer extendedState.Pub.Pub.Msgq.Close()

	pub := cereal.NewPublisher("mapdOut", cereal.MapdOutCreator)
	defer pub.Pub.Msgq.Close()
	state.Publisher = &pub

	sub := cereal.NewSubscriber("mapdIn", cereal.MapdInReader, false, false)
	defer sub.Sub.Msgq.Close()

	cli := cereal.NewSubscriber("mapdCli", cereal.MapdInReader, false, false)
	defer cli.Sub.Msgq.Close()

	gps := cereal.GetGpsSub()
	defer gps.Close()

	car := cereal.NewSubscriber("carState", cereal.CarStateReader, true, ms.Settings.SubscriberSettings.ShadowCarState)
	defer car.Sub.Msgq.Close()

	model := cereal.NewSubscriber("modelV2", cereal.ModelV2Reader, true, ms.Settings.SubscriberSettings.ShadowModelV2)
	defer model.Sub.Msgq.Close()

	selfdriveState := cereal.NewSubscriber("selfdriveState", cereal.SelfdriveStateReader, true, ms.Settings.SubscriberSettings.ShadowSelfdriveState)
	defer selfdriveState.Sub.Msgq.Close()

	lastLoopTime := time.Now()

	for {
		lastLoopDuration := time.Since(lastLoopTime)
		time.Sleep(max(ms.LOOP_DELAY-lastLoopDuration, 0))
		now := time.Now()
		extendedState.LoopRate.Add(now.Sub(lastLoopTime))
		lastLoopTime = now

		// handle settings inputs from openpilot/cli
		input, inputSuccess := sub.Read()
		if inputSuccess {
			ms.Settings.Handle(input)
		}
		cliInput, cliSuccess := cli.Read()
		if cliSuccess {
			ms.Settings.Handle(cliInput)
		}

		progress, success := ms.Settings.GetDownloadProgress()
		if success {
			extendedState.DownloadProgress = progress
		}

		carData, carStateSuccess := car.Read()
		if carStateSuccess {
			state.UpdateCarState(carData)
		}

		modelData, modelSuccess := model.Read()
		if modelSuccess {
			state.VisionCurveSpeed = calcVisionCurveSpeed(modelData, &state)
		}

		selfdriveData, selfdriveSuccess := selfdriveState.Read()
		if selfdriveSuccess {
			ms.Settings.SetPersonality(selfdriveData.Personality())
		}

		sample, gpsSuccess := gps.ReadSample()
		state.ProcessGps(sample, gpsSuccess, maps.FindWaysAroundPosition, time.Now())
		if state.RoadMatched() {
			state.UpdateRoadDependentCar()
			UpdateCurveSpeed(&state)
		}
		if err := state.Send(); err != nil {
			slog.Error("Failed to send update", "error", err)
		}
		if err := extendedState.Send(); err != nil {
			slog.Error("Failed to send extended update", "error", err)
		}
	}
}

func shadowRoot(args []string) (string, maps.SnapshotReceipt, error) {
	flags := flag.NewFlagSet("shadow", flag.ContinueOnError)
	root := flags.String("offline-root", "", "explicit existing offline tile directory")
	if err := flags.Parse(args); err != nil || flags.NArg() != 0 || *root == "" || !filepath.IsAbs(*root) {
		return "", maps.SnapshotReceipt{}, errors.New("shadow requires an absolute --offline-root and no other arguments")
	}
	info, err := os.Lstat(*root)
	if err != nil || !info.IsDir() {
		return "", maps.SnapshotReceipt{}, errors.New("shadow offline root must be an existing directory")
	}
	return maps.ResolveSnapshot(filepath.Clean(*root))
}

func runSnapshotAdmit(args []string) error {
	flags := flag.NewFlagSet("snapshot-admit", flag.ContinueOnError)
	root := flags.String("offline-root", "", "existing owned snapshot root")
	pbf := flags.String("input-pbf", "", "local OSM PBF input")
	archives := flags.String("archive-dir", "", "local group archive directory")
	minLat, minLon := flags.Float64("min-lat", 0, "aligned lower latitude"), flags.Float64("min-lon", 0, "aligned lower longitude")
	maxLat, maxLon := flags.Float64("max-lat", 0, "aligned upper latitude"), flags.Float64("max-lon", 0, "aligned upper longitude")
	overlap := flags.Float64("overlap", 0.001, "tile overlap in degrees")
	sourceURL := flags.String("source-url", "", "unverified caller-supplied origin URL")
	sourceDate := flags.String("source-date", "", "unverified caller-supplied extract date")
	if err := flags.Parse(args); err != nil || flags.NArg() != 0 || *root == "" || !filepath.IsAbs(*root) {
		return errors.New("snapshot admission requires absolute --offline-root and explicit bounds/input")
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	id, err := maps.AdmitSnapshot(ctx, maps.AdmitOptions{Root: filepath.Clean(*root),
		Bounds: [4]float64{*minLat, *minLon, *maxLat, *maxLon}, Overlap: *overlap,
		PBF: *pbf, ArchiveDir: *archives, SourceURL: *sourceURL, SourceDate: *sourceDate,
		SourceRevision: sourceRevision, UpstreamRevision: upstreamRevision, SourceDigest: sourceDigest})
	if err == nil {
		slog.Info("offline snapshot selected for next shadow start", "generation", id)
	}
	return err
}

func runSnapshotFetch(args []string) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	return runSnapshotFetchContext(ctx, args, http.DefaultClient)
}

// The client seam lets tests intercept the fixed production URL beneath the
// real CLI parser. No URL override is exposed to callers.
func runSnapshotFetchContext(ctx context.Context, args []string, client *http.Client) error {
	flags := flag.NewFlagSet("snapshot-fetch", flag.ContinueOnError)
	root := flags.String("offline-root", "", "existing owned snapshot root")
	minLat, minLon := flags.Float64("min-lat", 0, "aligned lower latitude"), flags.Float64("min-lon", 0, "aligned lower longitude")
	maxLat, maxLon := flags.Float64("max-lat", 0, "aligned upper latitude"), flags.Float64("max-lon", 0, "aligned upper longitude")
	overlap := flags.Float64("overlap", 0.001, "tile overlap in degrees")
	maxBytes := flags.Int64("max-bytes", 0, "required total archive transfer budget in bytes")
	if err := flags.Parse(args); err != nil || flags.NArg() != 0 || *root == "" || !filepath.IsAbs(*root) || *maxBytes <= 0 {
		return errors.New("snapshot fetch requires absolute --offline-root, aligned bounds, and positive --max-bytes")
	}
	id, err := maps.FetchAndAdmitSnapshot(ctx, maps.FetchOptions{
		AdmitOptions: maps.AdmitOptions{Root: filepath.Clean(*root), Bounds: [4]float64{*minLat, *minLon, *maxLat, *maxLon},
			Overlap: *overlap, SourceRevision: sourceRevision, UpstreamRevision: upstreamRevision, SourceDigest: sourceDigest},
		MaxBytes: *maxBytes,
	}, client)
	if err == nil {
		slog.Info("fetched offline snapshot selected for next shadow start; source provenance unverified",
			"generation", id, "attribution", maps.SnapshotAttributionNotice)
	}
	return err
}

// shadowStep is the production loop's road computation and wire boundary.
// Only GPS and validated tile data can influence its diagnostic output.
func shadowStep(state *State, readGPS func() (cereal.GpsSample, bool), load MapLoader, now time.Time) (*capnp.Message, error) {
	sample, ok := readGPS()
	state.ProcessGps(sample, ok, load, now)
	return state.BuildMessage()
}

// runShadowLoop is the production shadow pump with injectable ticks and
// transport for deterministic lifecycle/serialization tests.
func runShadowLoop(ctx context.Context, ticks <-chan time.Time, state *State, readGPS func() (cereal.GpsSample, bool), load MapLoader, publish func(*capnp.Message) error) {
	for {
		select {
		case <-ctx.Done():
			return
		case now, ok := <-ticks:
			if !ok {
				return
			}
			msg, err := shadowStep(state, readGPS, load, now)
			if err != nil {
				slog.Error("shadow map observation failed", "error", err)
				continue
			}
			if err := publish(msg); err != nil {
				slog.Error("shadow map observation publish failed", "error", err)
			}
		}
	}
}

func runShadowArgs(args []string) error {
	root, receipt, err := shadowRoot(args)
	if err != nil {
		return err
	}
	if err := initShadowDefaults(); err != nil {
		return err
	}
	initShadowIPC()
	// Do not load persistent MapdSettings or construct MapdIn/CLI, download,
	// carState, modelV2, selfdriveState, or extended-status subscribers.
	state := State{ShadowOnly: true, SnapshotID: filepath.Base(root)}
	state.Init()
	slog.Info("shadow offline snapshot pinned", "generation", state.SnapshotID, "producer_session", state.ProducerSession)
	pub := cereal.NewPublisher("mapdOut", cereal.MapdOutCreator)
	defer pub.Pub.Msgq.Close()
	gps := cereal.GetGpsSub() // bundled subscriber settings use ordinary GPS queues
	defer gps.Close()
	load := maps.SnapshotLoader(root, receipt)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	ticker := time.NewTicker(ms.LOOP_DELAY)
	defer ticker.Stop()
	runShadowLoop(ctx, ticker.C, &state, gps.ReadSample, load, pub.Send)
	return nil
}

// Host msgq uses msgq_<OPENPILOT_PREFIX>/<service> and the service registry's
// queue size. gomsgq's marker-file fallback is not a reliable startup signal.
// Apply this only in the separate shadow process; the full-provider path is
// intentionally unchanged.
func initShadowIPC() {
	gomsgq.OPENPILOT_PREFIX = os.Getenv("OPENPILOT_PREFIX")
	gomsgq.USE_MSGQ_PREFIX = "true"
	ms.ServiceQueueSize["mapdOut"] = ms.QUEUE_SIZE_SMALL
}

func initShadowDefaults() error {
	defaults, err := ms.BundledDefaults()
	if err != nil {
		return err
	}
	// Existing matcher helpers read this package setting for lane geometry and
	// conditional limits. Use only embedded values; never read device overrides.
	ms.Settings = defaults
	return nil
}
