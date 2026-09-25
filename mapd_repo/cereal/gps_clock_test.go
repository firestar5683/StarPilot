package cereal

import "testing"

func TestGpsStartupFenceAndStableMonotonicToBootConversion(t *testing.T) {
	mono := uint64(10_000_000_000)
	offset := uint64(3_000_000_000)
	internal, iq := wireQueue(GpsLocationReader)
	external, eq := wireQueue(GpsLocationExternalReader)
	s := GpsSub{gpsLocation: internal, gpsLocationExternal: external,
		clock: func() clockSample { return clockSample{mono - 1_000, mono + offset, mono + 1_000} }}
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono-100, true, true, 3, 4, 5))
	if sample, ok := s.ReadSample(); ok || sample.Source != GpsSourceNone {
		t.Fatalf("startup consumed a queued pre-start GPS event: %+v %v", sample, ok)
	}
	mono += 100_000_000
	raw := mono - 10_000_000
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, raw, true, true, 3, 4, 5))
	sample, ok := s.ReadSample()
	if !ok || sample.Source != GpsSourceExternal || sample.SourceGeneration != 1 || sample.FixMonoTime != raw+offset-1_000 {
		t.Fatalf("post-start Python timestamp did not convert to boot time: %+v %v", sample, ok)
	}
	// A bounded read-skew change cannot masquerade as a suspend step or renew
	// the original fix timestamp during 20 Hz reuse.
	s.clock = func() clockSample { return clockSample{mono - 10_000, mono + offset, mono + 5_000} }
	mono += 50_000_000
	sample, ok = s.ReadSample()
	if !ok || sample.SourceChanged || sample.NewFix || sample.FixMonoTime != raw+offset-1_000 {
		t.Fatalf("stable offset jitter changed original fix age: %+v %v", sample, ok)
	}
	_ = iq
}

func TestGpsSuspendFencesQueuedEventsAndRequiresPostResumeFix(t *testing.T) {
	mono := uint64(10_000_000_000)
	offset := uint64(3_000_000_000)
	internal, iq := wireQueue(GpsLocationReader)
	external, eq := wireQueue(GpsLocationExternalReader)
	s := GpsSub{gpsLocation: internal, gpsLocationExternal: external,
		clock: func() clockSample { return clockSample{mono, mono + offset, mono} }}
	s.ReadSample() // establish startup fence
	mono += 100_000_000
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono, true, true, 3, 4, 5))
	if sample, ok := s.ReadSample(); !ok || sample.Source != GpsSourceExternal || sample.SourceGeneration != 1 {
		t.Fatalf("initial source unavailable: %+v %v", sample, ok)
	}
	preSuspend := mono
	mono += 1_000_000 // only 1 ms of active time despite a long suspend
	offset += 3_000_000_000
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, preSuspend, true, true, 9, 9, 5))
	*iq = append(*iq, gpsWire(t, GpsSourceInternal, preSuspend, true, true, 1, 2, 5))
	sample, ok := s.ReadSample()
	if ok || sample.Source != GpsSourceNone || !sample.SourceChanged || sample.SourceGeneration != 2 {
		t.Fatalf("resume did not invalidate and fence queued fixes: %+v %v", sample, ok)
	}
	mono += 100_000_000
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, preSuspend, false, false, 9, 9, 5))
	sample, ok = s.ReadSample()
	if ok || sample.SourceGeneration != 2 {
		t.Fatalf("queued pre-suspend invalid event altered post-resume state: %+v %v", sample, ok)
	}
	mono += 100_000_000
	*iq = append(*iq, gpsWire(t, GpsSourceInternal, mono-1, true, true, 1, 2, 5))
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceInternal || sample.SourceGeneration != 3 || sample.FixMonoTime != mono-1+offset {
		t.Fatalf("new post-resume source did not recover: %+v %v", sample, ok)
	}
	mono += 100_000_000
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono+1, true, true, 9, 9, 5))
	sample, ok = s.ReadSample()
	if !ok || sample.Source != GpsSourceInternal || sample.FixMonoTime != mono-100_000_001+offset {
		t.Fatalf("future event replaced recovered fix: %+v %v", sample, ok)
	}
}

func TestGpsUncertainClockPairInvalidatesHeldEvidence(t *testing.T) {
	mono := uint64(10_000_000_000)
	clock := clockSample{mono, mono, mono}
	internal, _ := wireQueue(GpsLocationReader)
	external, eq := wireQueue(GpsLocationExternalReader)
	s := GpsSub{gpsLocation: internal, gpsLocationExternal: external, clock: func() clockSample { return clock }}
	s.ReadSample()
	mono += 100_000_000
	clock = clockSample{mono, mono, mono}
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono, true, true, 3, 4, 5))
	if _, ok := s.ReadSample(); !ok {
		t.Fatal("pre-skew fix unavailable")
	}
	mono += 100_000_000
	clock = clockSample{mono - 2_000_000, mono, mono}
	if sample, ok := s.ReadSample(); ok || sample.Source != GpsSourceNone || sample.SourceGeneration != 2 {
		t.Fatalf("uncertain paired read retained source: %+v %v", sample, ok)
	}
	mono += 100_000_000
	clock = clockSample{mono, mono, mono}
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono-1, true, true, 3, 4, 5))
	if sample, ok := s.ReadSample(); ok || sample.Source != GpsSourceNone {
		t.Fatalf("uncertain-pair recovery accepted a queued fix: %+v %v", sample, ok)
	}
	mono += 100_000_000
	clock = clockSample{mono, mono, mono}
	*eq = append(*eq, gpsWire(t, GpsSourceExternal, mono, true, true, 3, 4, 5))
	if sample, ok := s.ReadSample(); !ok || sample.SourceGeneration != 3 {
		t.Fatalf("post-fence fix failed to recover: %+v %v", sample, ok)
	}
}
