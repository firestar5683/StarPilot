package maps

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func TestPreparedSnapshotSelectionAndRecovery(t *testing.T) {
	root := t.TempDir()
	oldID, err := AdmitSnapshot(context.Background(), AdmitOptions{Root: root,
		Bounds: [4]float64{35, -98, 35.25, -97.75}, Overlap: .001,
		PBF:            filepath.Join("..", "testdata", "synthetic_snapshot.osm.pbf"),
		SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"})
	if err != nil {
		t.Fatal(err)
	}
	archiveDir := filepath.Join(t.TempDir(), "archives")
	if err := os.MkdirAll(filepath.Join(archiveDir, "0"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(archiveDir, "0", "0.tar.gz"), snapshotGroupArchive(t, 0, 0), 0o600); err != nil {
		t.Fatal(err)
	}
	id, err := PrepareSnapshot(context.Background(), AdmitOptions{Root: root, Bounds: [4]float64{0, 0, 2, 2},
		Overlap: .001, ArchiveDir: archiveDir, SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"})
	if err != nil {
		t.Fatal(err)
	}
	selected, _, err := ResolveSnapshot(root)
	if err != nil || filepath.Base(selected) != oldID {
		t.Fatalf("prepare changed live selection: %v %s", err, selected)
	}
	if err := SelectPreparedSnapshot(context.Background(), root, id, ""); err == nil {
		t.Fatal("stale expected selector accepted")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := SelectPreparedSnapshot(ctx, root, id, oldID); err == nil {
		t.Fatal("canceled selection accepted")
	}
	_, receipt, err := verifySnapshot(root, id)
	if err != nil {
		t.Fatal(err)
	}
	tile := filepath.Join(root, "generations", id, receipt.Tiles[0].Path)
	original, err := os.ReadFile(tile)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(tile, []byte("tampered tile"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := SelectPreparedSnapshot(context.Background(), root, id, oldID); err == nil {
		t.Fatal("modified prepared generation selected")
	}
	if err := os.WriteFile(tile, original, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := SelectPreparedSnapshot(context.Background(), root, id, oldID); err != nil {
		t.Fatal(err)
	}
	selected, _, err = ResolveSnapshot(root)
	if err != nil || filepath.Base(selected) != id {
		t.Fatalf("prepared generation not selected: %v %s", err, selected)
	}
	if err := SelectPreparedSnapshot(context.Background(), root, oldID, oldID); err == nil {
		t.Fatal("stale second selector accepted")
	}
}

func TestManagedFetchProgressAndDiskBudget(t *testing.T) {
	archive := snapshotGroupArchive(t, 0, 0)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(archive) }))
	defer server.Close()
	client := &http.Client{Transport: localArchiveTransport{server}}
	root := t.TempDir()
	o := fetchOptions(root, [4]float64{0, 0, 2, 2}, int64(len(archive)*2))
	o.PrepareOnly = true
	o.MaxNewDiskBytes = int64(len(archive))
	if _, err := FetchAndAdmitSnapshot(context.Background(), o, client); err == nil {
		t.Fatal("budget covering only download accepted full admission")
	}
	if _, err := os.Stat(filepath.Join(root, "current.json")); !os.IsNotExist(err) {
		t.Fatalf("failed budget changed selector: %v", err)
	}
	o.MaxNewDiskBytes = 16 << 20
	var phases []FetchProgress
	o.Progress = func(progress FetchProgress) error {
		phases = append(phases, progress)
		return nil
	}
	id, err := FetchAndAdmitSnapshot(context.Background(), o, client)
	if err != nil {
		t.Fatal(err)
	}
	if len(phases) != 3 || phases[0].Phase != "transferring" || phases[0].Completed != 0 ||
		phases[1].Phase != "transferring" || phases[1].Completed != 1 || phases[2].Phase != "validating" ||
		phases[2].Completed != 1 || phases[2].Transferred != int64(len(archive)) {
		t.Fatalf("progress did not represent completed archive: %+v", phases)
	}
	if _, err := os.Stat(filepath.Join(root, "current.json")); !os.IsNotExist(err) {
		t.Fatalf("prepare selected snapshot: %v", err)
	}
	if err := SelectPreparedSnapshot(context.Background(), root, id, ""); err != nil {
		t.Fatal(err)
	}
}

func TestSnapshotFetchRetryCountsFailedBytesAndCleansPartial(t *testing.T) {
	archive := snapshotGroupArchive(t, 0, 0)
	for _, tc := range []struct {
		name        string
		budget      int64
		wantSuccess bool
	}{
		{"retry-success", int64(len(archive) * 2), true},
		{"retry-budget-exhausted", int64(len(archive) + len(archive)/2 - 1), false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			requests := 0
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requests++
				if requests == 1 {
					w.Header().Set("Content-Length", strconv.Itoa(len(archive)))
					_, _ = w.Write(archive[:len(archive)/2])
					return
				}
				_, _ = w.Write(archive)
			}))
			defer server.Close()
			root := t.TempDir()
			var progress []FetchProgress
			o := fetchOptions(root, [4]float64{0, 0, 2, 2}, tc.budget)
			o.Progress = func(p FetchProgress) error { progress = append(progress, p); return nil }
			_, err := FetchAndAdmitSnapshot(context.Background(), o, &http.Client{Transport: localArchiveTransport{server}})
			if (err == nil) != tc.wantSuccess || requests != 2 {
				t.Fatalf("retry result=%v requests=%d", err, requests)
			}
			if tc.wantSuccess {
				if len(progress) != 3 || progress[1].Transferred != int64(len(archive)+len(archive)/2) {
					t.Fatalf("failed transfer bytes omitted: %+v", progress)
				}
			} else if _, statErr := os.Stat(filepath.Join(root, "current.json")); !os.IsNotExist(statErr) {
				t.Fatalf("failed retry selected: %v", statErr)
			}
			entries, readErr := os.ReadDir(root)
			if readErr != nil {
				t.Fatal(readErr)
			}
			for _, entry := range entries {
				if strings.HasPrefix(entry.Name(), ".snapshot-fetch-") {
					t.Fatal("retry staging retained")
				}
			}
		})
	}
}

func TestSnapshotFetchPermanentFailureDoesNotRetry(t *testing.T) {
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()
	root := t.TempDir()
	_, err := FetchAndAdmitSnapshot(context.Background(), fetchOptions(root, [4]float64{0, 0, 2, 2}, 1000),
		&http.Client{Transport: localArchiveTransport{server}})
	if err == nil || requests != 1 {
		t.Fatalf("permanent failure retried: %v %d", err, requests)
	}
}

func TestConcurrentPreparedSelectionsHaveOneWinner(t *testing.T) {
	root := t.TempDir()
	archiveDir := filepath.Join(t.TempDir(), "archives")
	if err := os.MkdirAll(filepath.Join(archiveDir, "0"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(archiveDir, "0", "0.tar.gz"), snapshotGroupArchive(t, 0, 0), 0o600); err != nil {
		t.Fatal(err)
	}
	var ids [2]string
	for i := range ids {
		id, err := PrepareSnapshot(context.Background(), AdmitOptions{Root: root, Bounds: [4]float64{0, 0, 2, 2},
			Overlap: .001, ArchiveDir: archiveDir, SourceRevision: "fixture-" + strconv.Itoa(i),
			UpstreamRevision: "fixture", SourceDigest: "fixture"})
		if err != nil {
			t.Fatal(err)
		}
		ids[i] = id
	}
	if ids[0] == ids[1] {
		t.Fatal("distinct preparation identities collapsed")
	}
	start := make(chan struct{})
	results := make(chan error, 2)
	for _, id := range ids {
		go func(id string) {
			<-start
			results <- SelectPreparedSnapshot(context.Background(), root, id, "")
		}(id)
	}
	close(start)
	wins := 0
	for i := 0; i < 2; i++ {
		if <-results == nil {
			wins++
		}
	}
	if wins != 1 {
		t.Fatalf("expected exactly one admission-lock winner, got %d", wins)
	}
	selected, _, err := ResolveSnapshot(root)
	if err != nil || (filepath.Base(selected) != ids[0] && filepath.Base(selected) != ids[1]) {
		t.Fatalf("winner not selected: %v %s", err, selected)
	}
}

func TestManagedProgressFailurePreventsSelection(t *testing.T) {
	archive := snapshotGroupArchive(t, 0, 0)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(archive) }))
	defer server.Close()
	root := t.TempDir()
	o := fetchOptions(root, [4]float64{0, 0, 2, 2}, int64(len(archive)))
	o.MaxNewDiskBytes = 16 << 20
	o.Progress = func(progress FetchProgress) error {
		if progress.Phase == "validating" {
			return errors.New("owner canceled before validation")
		}
		return nil
	}
	if _, err := FetchAndAdmitSnapshot(context.Background(), o, &http.Client{Transport: localArchiveTransport{server}}); err == nil {
		t.Fatal("owner progress failure ignored")
	}
	if _, err := os.Stat(filepath.Join(root, "current.json")); !os.IsNotExist(err) {
		t.Fatalf("progress failure selected generation: %v", err)
	}
}

func TestSnapshotFetchTransientStatusRetriesButCancellationStops(t *testing.T) {
	archive := snapshotGroupArchive(t, 0, 0)
	for _, cancelFirst := range []bool{false, true} {
		t.Run(strconv.FormatBool(cancelFirst), func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			requests := 0
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requests++
				if requests == 1 {
					w.WriteHeader(http.StatusServiceUnavailable)
					if cancelFirst {
						cancel()
					}
					return
				}
				_, _ = w.Write(archive)
			}))
			defer server.Close()
			root := t.TempDir()
			_, err := FetchAndAdmitSnapshot(ctx, fetchOptions(root, [4]float64{0, 0, 2, 2}, int64(len(archive))),
				&http.Client{Transport: localArchiveTransport{server}})
			if cancelFirst {
				if err == nil || requests != 1 {
					t.Fatalf("canceled retry continued: %v %d", err, requests)
				}
			} else if err != nil || requests != 2 {
				t.Fatalf("transient status not retried: %v %d", err, requests)
			}
		})
	}
}
