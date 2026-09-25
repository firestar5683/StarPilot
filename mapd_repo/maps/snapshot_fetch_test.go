package maps

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"capnproto.org/go/capnp/v3"
	"pfeifer.dev/mapd/cereal/offline"
)

type localArchiveTransport struct {
	server *httptest.Server
}

func (t localArchiveTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if req.URL.Scheme != "https" || req.URL.Host != "map-data.pfeifer.dev" {
		return nil, errors.New("test refused nonfixed archive origin")
	}
	copy := req.Clone(req.Context())
	u, err := url.Parse(t.server.URL)
	if err != nil {
		return nil, err
	}
	copy.URL.Scheme, copy.URL.Host = u.Scheme, u.Host
	return http.DefaultTransport.RoundTrip(copy)
}

func fetchOptions(root string, bounds [4]float64, budget int64) FetchOptions {
	return FetchOptions{AdmitOptions: AdmitOptions{Root: root, Bounds: bounds, Overlap: .001,
		SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"}, MaxBytes: budget}
}

func snapshotGroupArchive(t *testing.T, lat, lon int) []byte {
	t.Helper()
	paths, err := expectedSnapshotTiles([4]float64{float64(lat), float64(lon), float64(lat + 2), float64(lon + 2)})
	if err != nil {
		t.Fatal(err)
	}
	var buffer bytes.Buffer
	gz := gzip.NewWriter(&buffer)
	tarWriter := tar.NewWriter(gz)
	for _, rel := range paths {
		parts := strings.Split(filepath.Base(rel), "_")
		if len(parts) != 4 {
			t.Fatal(rel)
		}
		var box [4]float64
		for i, part := range parts {
			box[i], err = strconv.ParseFloat(part, 64)
			if err != nil {
				t.Fatal(err)
			}
		}
		msg, segment, err := capnp.NewMessage(capnp.SingleSegment(nil))
		if err != nil {
			t.Fatal(err)
		}
		tile, err := offline.NewRootOffline(segment)
		if err != nil {
			t.Fatal(err)
		}
		tile.SetMinLat(box[0])
		tile.SetMinLon(box[1])
		tile.SetMaxLat(box[2])
		tile.SetMaxLon(box[3])
		tile.SetOverlap(.001)
		if _, err := tile.NewWays(0); err != nil {
			t.Fatal(err)
		}
		data, err := msg.MarshalPacked()
		if err != nil {
			t.Fatal(err)
		}
		if err := tarWriter.WriteHeader(&tar.Header{Name: "offline/" + rel, Typeflag: tar.TypeReg, Mode: 0o644, Size: int64(len(data))}); err != nil {
			t.Fatal(err)
		}
		if _, err := tarWriter.Write(data); err != nil {
			t.Fatal(err)
		}
	}
	if err := tarWriter.Close(); err != nil {
		t.Fatal(err)
	}
	if err := gz.Close(); err != nil {
		t.Fatal(err)
	}
	return buffer.Bytes()
}

func TestSnapshotFetchTwoLongitudeGroupsSucceedAtomically(t *testing.T) {
	first, second := snapshotGroupArchive(t, 0, 0), snapshotGroupArchive(t, 0, 2)
	bodies := map[string][]byte{"/offline/0/0.tar.gz": first, "/offline/0/2.tar.gz": second}
	var paths []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		body, ok := bodies[r.URL.Path]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		w.Write(body)
	}))
	defer server.Close()
	root := t.TempDir()
	id, err := FetchAndAdmitSnapshot(context.Background(), fetchOptions(root, [4]float64{0, 0, 2, 4}, int64(len(first)+len(second))),
		&http.Client{Transport: localArchiveTransport{server}})
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 2 || paths[0] != "/offline/0/0.tar.gz" || paths[1] != "/offline/0/2.tar.gz" {
		t.Fatalf("wrong bounded group list: %v", paths)
	}
	selected, receipt, err := ResolveSnapshot(root)
	if err != nil || filepath.Base(selected) != id || len(receipt.Inputs) != 2 || len(receipt.Tiles) != 128 {
		t.Fatalf("two-group selection incomplete: %v %s %+v", err, selected, receipt)
	}
}

func TestSnapshotFetchUsesFixedOriginAndAdmitsCompleteSyntheticArchive(t *testing.T) {
	archive := archiveTiles(t, 64)
	var paths []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		w.Write(archive)
	}))
	defer server.Close()
	root := t.TempDir()
	id, err := FetchAndAdmitSnapshot(context.Background(), fetchOptions(root, [4]float64{0, 0, 2, 2}, int64(len(archive))),
		&http.Client{Transport: localArchiveTransport{server}})
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 1 || paths[0] != "/offline/0/0.tar.gz" {
		t.Fatalf("unexpected remote group list: %v", paths)
	}
	_, receipt, err := ResolveSnapshot(root)
	if err != nil || receipt.SourceKind != "provided-group-archives" || receipt.SourceVerified || receipt.SourceDate != "" ||
		receipt.SourceURL != snapshotArchiveOrigin+"/offline/" || len(receipt.Inputs) != 1 || len(receipt.Tiles) != 64 {
		t.Fatalf("bad selected receipt: %v %+v", err, receipt)
	}
	digest := sha256.Sum256(archive)
	if receipt.Inputs[0].Name != "0/0.tar.gz" || receipt.Inputs[0].Size != int64(len(archive)) ||
		receipt.Inputs[0].SHA256 != hex.EncodeToString(digest[:]) {
		t.Fatalf("receipt did not record exact served archive: %+v", receipt.Inputs)
	}
	if _, err := os.Stat(filepath.Join(root, "generations", id, "receipt.json")); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), ".snapshot-fetch-") {
			t.Fatal("owned fetch staging was not cleaned")
		}
	}
}

func TestSnapshotFetchFailuresPreservePreviousSelection(t *testing.T) {
	archive := archiveTiles(t, 64)
	tests := []struct {
		name   string
		status int
		body   []byte
		red    string
		budget int64
		bounds [4]float64
	}{
		{"http-failure", http.StatusServiceUnavailable, nil, "", int64(len(archive) * 2), [4]float64{0, 0, 2, 2}},
		{"truncated-gzip", http.StatusOK, archive[:len(archive)-8], "", int64(len(archive) * 2), [4]float64{0, 0, 2, 2}},
		{"cross-origin-redirect", http.StatusFound, nil, "https://other.example/offline/0/0.tar.gz", int64(len(archive) * 2), [4]float64{0, 0, 2, 2}},
		{"global-budget", http.StatusOK, archive, "", int64(len(archive)*2 - 1), [4]float64{0, 0, 2, 4}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			oldID, err := AdmitSnapshot(context.Background(), AdmitOptions{Root: root, Bounds: [4]float64{35, -98, 35.25, -97.75},
				Overlap: .001, PBF: filepath.Join("..", "testdata", "synthetic_snapshot.osm.pbf"),
				SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"})
			if err != nil {
				t.Fatal(err)
			}
			var paths []string
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				paths = append(paths, r.URL.Path)
				if tc.red != "" {
					w.Header().Set("Location", tc.red)
				}
				w.WriteHeader(tc.status)
				w.Write(tc.body)
			}))
			defer server.Close()
			_, err = FetchAndAdmitSnapshot(context.Background(), fetchOptions(root, tc.bounds, tc.budget),
				&http.Client{Transport: localArchiveTransport{server}})
			if err == nil {
				t.Fatal("failed fetch selected an incomplete generation")
			}
			selected, _, err := ResolveSnapshot(root)
			if err != nil || filepath.Base(selected) != oldID {
				t.Fatalf("prior selector changed after fetch failure: %v %s", err, selected)
			}
			if tc.name == "global-budget" && (len(paths) != 2 || paths[0] != "/offline/0/0.tar.gz" || paths[1] != "/offline/0/2.tar.gz") {
				t.Fatalf("global budget did not span both groups: %v", paths)
			}
		})
	}
}

func TestSnapshotFetchRejectsInvalidArgumentsBeforeNetwork(t *testing.T) {
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { requests++ }))
	defer server.Close()
	client := &http.Client{Transport: localArchiveTransport{server}}
	root := t.TempDir()
	for _, options := range []FetchOptions{
		fetchOptions(root, [4]float64{0, 0, 2, 2}, 0),
		fetchOptions(root, [4]float64{0, 0, 2, 1}, 100),
		fetchOptions(root, [4]float64{-90, -180, 90, 180}, 100),
	} {
		if _, err := FetchAndAdmitSnapshot(context.Background(), options, client); err == nil {
			t.Fatalf("invalid request accepted: %+v", options)
		}
	}
	if requests != 0 {
		t.Fatalf("invalid selection made %d network requests", requests)
	}
}

func TestSnapshotFetchCancellationKeepsOldSelector(t *testing.T) {
	archive := archiveTiles(t, 64)
	root := t.TempDir()
	oldID, err := AdmitSnapshot(context.Background(), AdmitOptions{Root: root, Bounds: [4]float64{35, -98, 35.25, -97.75},
		Overlap: .001, PBF: filepath.Join("..", "testdata", "synthetic_snapshot.osm.pbf"),
		SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"})
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		if requests == 2 {
			cancel()
			return
		}
		io.Copy(w, strings.NewReader(string(archive)))
	}))
	defer server.Close()
	if _, err := FetchAndAdmitSnapshot(ctx, fetchOptions(root, [4]float64{0, 0, 2, 4}, int64(len(archive)*3)),
		&http.Client{Transport: localArchiveTransport{server}}); err == nil {
		t.Fatal("canceled fetch admitted an incomplete region")
	}
	selected, _, err := ResolveSnapshot(root)
	if err != nil || filepath.Base(selected) != oldID {
		t.Fatalf("cancellation changed selected generation: %v %s", err, selected)
	}
}
