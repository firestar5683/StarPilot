package main

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"pfeifer.dev/mapd/maps"
)

type fixedOriginTestTransport struct {
	server *httptest.Server
}

func (t fixedOriginTestTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if req.URL.Scheme != "https" || req.URL.Host != "map-data.pfeifer.dev" {
		return nil, errors.New("test prevented nonfixed archive request")
	}
	copy := req.Clone(req.Context())
	serverURL, err := url.Parse(t.server.URL)
	if err != nil {
		return nil, err
	}
	copy.URL.Scheme, copy.URL.Host = serverURL.Scheme, serverURL.Host
	return http.DefaultTransport.RoundTrip(copy)
}

func generatedSnapshotArchive(t *testing.T) []byte {
	t.Helper()
	root := t.TempDir()
	_, err := maps.AdmitSnapshot(context.Background(), maps.AdmitOptions{Root: root,
		Bounds: [4]float64{34, -98, 36, -96}, Overlap: .001,
		PBF:            filepath.Join("testdata", "synthetic_snapshot.osm.pbf"),
		SourceRevision: "fixture", UpstreamRevision: "fixture", SourceDigest: "fixture"})
	if err != nil {
		t.Fatal(err)
	}
	selected, receipt, err := maps.ResolveSnapshot(root)
	if err != nil || len(receipt.Tiles) != 64 {
		t.Fatalf("actual generator did not produce one complete group: %v %+v", err, receipt)
	}
	var buffer bytes.Buffer
	gz := gzip.NewWriter(&buffer)
	tw := tar.NewWriter(gz)
	for _, tile := range receipt.Tiles {
		data, err := os.ReadFile(filepath.Join(selected, tile.Path))
		if err != nil {
			t.Fatal(err)
		}
		if err := tw.WriteHeader(&tar.Header{Name: "offline/" + tile.Path, Typeflag: tar.TypeReg,
			Mode: 0o644, Size: int64(len(data))}); err != nil {
			t.Fatal(err)
		}
		if _, err := tw.Write(data); err != nil {
			t.Fatal(err)
		}
	}
	if err := tw.Close(); err != nil {
		t.Fatal(err)
	}
	if err := gz.Close(); err != nil {
		t.Fatal(err)
	}
	return buffer.Bytes()
}

func TestSnapshotFetchCLIParserWithGeneratedPBFAndSyntheticHTTP(t *testing.T) {
	archive := generatedSnapshotArchive(t)
	var paths []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		if r.Header.Get("Accept-Encoding") != "identity" {
			t.Error("request allowed transparent HTTP decompression")
		}
		if r.URL.Path == "/offline/34/-98.tar.gz" {
			w.Header().Set("Location", "/archive")
			w.WriteHeader(http.StatusFound)
			return
		}
		if r.URL.Path != "/archive" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		io.Copy(w, bytes.NewReader(archive))
	}))
	defer server.Close()
	root := t.TempDir()
	args := []string{"--offline-root", root, "--min-lat", "34", "--min-lon", "-98",
		"--max-lat", "36", "--max-lon", "-96", "--max-bytes", strconv.Itoa(len(archive))}
	client := &http.Client{Transport: fixedOriginTestTransport{server}}
	if err := runSnapshotFetchContext(context.Background(), args, client); err != nil {
		t.Fatal(err)
	}
	selected, receipt, err := maps.ResolveSnapshot(root)
	if err != nil || selected == "" || len(receipt.Inputs) != 1 || len(receipt.Tiles) != 64 || receipt.SourceVerified {
		t.Fatalf("CLI failed to select actual generated tile group: %v %+v", err, receipt)
	}
	if len(paths) != 2 || paths[0] != "/offline/34/-98.tar.gz" || paths[1] != "/archive" {
		t.Fatalf("unexpected CLI request/redirect path: %v", paths)
	}
	if err := runSnapshotFetchContext(context.Background(), args[:len(args)-2], client); err == nil || len(paths) != 2 {
		t.Fatal("missing transfer budget reached HTTP")
	}
}
