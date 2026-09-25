package settings

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"errors"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"
)

type archiveTransport struct {
	body         []byte
	status       int
	responseBody io.ReadCloser
}

func (a archiveTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	body := a.responseBody
	if body == nil {
		body = io.NopCloser(bytes.NewReader(a.body))
	}
	contentLength := int64(len(a.body))
	if a.responseBody != nil {
		contentLength = -1
	}
	return &http.Response{StatusCode: a.status, Status: http.StatusText(a.status), Body: body, ContentLength: contentLength, Header: make(http.Header), Request: req}, nil
}
func clientFor(data []byte, status int) *http.Client {
	return &http.Client{Transport: archiveTransport{body: data, status: status}}
}

type archiveEntry struct {
	name string
	kind byte
	data string
}

func archiveFor(t *testing.T, entries []archiveEntry, suffix []byte) []byte {
	t.Helper()
	var b bytes.Buffer
	gz := gzip.NewWriter(&b)
	tw := tar.NewWriter(gz)
	for _, e := range entries {
		h := &tar.Header{Name: e.name, Mode: 0644, Size: int64(len(e.data)), Typeflag: e.kind}
		if e.kind == tar.TypeDir {
			h.Size = 0
		}
		if err := tw.WriteHeader(h); err != nil {
			t.Fatal(err)
		}
		if e.kind == tar.TypeReg {
			if _, err := tw.Write([]byte(e.data)); err != nil {
				t.Fatal(err)
			}
		}
	}
	if err := tw.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := gz.Write(suffix); err != nil {
		t.Fatal(err)
	}
	if err := gz.Close(); err != nil {
		t.Fatal(err)
	}
	return b.Bytes()
}
func oneTile(t *testing.T, name, data string) []byte {
	return archiveFor(t, []archiveEntry{{name, tar.TypeReg, data}}, nil)
}
func readTile(t *testing.T, base, name string) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(base, name))
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}
func setupExisting(t *testing.T) (string, string) {
	t.Helper()
	base := filepath.Join(t.TempDir(), "maps")
	name := "offline/0/0/0.000000_0.000000_0.200000_0.200000"
	if err := os.MkdirAll(filepath.Join(base, "offline/0/0"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(base, name), []byte("existing-long-content"), 0644); err != nil {
		t.Fatal(err)
	}
	return base, name
}

func TestCheckedGroupInstallPreservesOldAndReplacesAtomically(t *testing.T) {
	base, name := setupExisting(t)
	sentinel := filepath.Join(filepath.Dir(base), "sentinel")
	if err := os.WriteFile(sentinel, []byte("untouched"), 0644); err != nil {
		t.Fatal(err)
	}
	bad := oneTile(t, name, "new")
	badFooter := append([]byte(nil), bad...)
	badFooter[len(badFooter)-8] ^= 0x01
	cases := []struct {
		name   string
		body   []byte
		status int
	}{
		{"http503", bad, 503}, {"bad_gzip", []byte("not gzip"), 200},
		{"truncated_gzip", bad[:len(bad)-4], 200},
		{"bad_gzip_footer", badFooter, 200},
		{"traversal", oneTile(t, "../sentinel", "bad"), 200},
		{"absolute", oneTile(t, "/sentinel", "bad"), 200},
		{"wrong_group", oneTile(t, "offline/2/0/tile", "bad"), 200},
		{"symlink_member", archiveFor(t, []archiveEntry{{name, tar.TypeSymlink, ""}}, nil), 200},
		{"duplicate", archiveFor(t, []archiveEntry{{name, tar.TypeReg, "a"}, {name, tar.TypeReg, "b"}}, nil), 200},
		{"trailing_tar", archiveFor(t, []archiveEntry{{name, tar.TypeReg, "new"}}, []byte("bad")), 200},
		{"concatenated_gzip", append(append([]byte{}, bad...), bad...), 200},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if err := installGroupArchive(context.Background(), clientFor(tc.body, tc.status), "https://synthetic.invalid/data", base, 0, 0); err == nil {
				t.Fatal("expected rejection")
			}
			if got := readTile(t, base, name); got != "existing-long-content" {
				t.Fatalf("old tile changed: %q", got)
			}
			if outside, err := os.ReadFile(sentinel); err != nil || string(outside) != "untouched" {
				t.Fatalf("outside file changed: %q %v", outside, err)
			}
		})
	}
	if err := installGroupArchive(context.Background(), clientFor(bad, 200), "https://synthetic.invalid/data", base, 0, 0); err != nil {
		t.Fatal(err)
	}
	if got := readTile(t, base, name); got != "new" {
		t.Fatalf("short replacement retained suffix: %q", got)
	}
	entries, err := os.ReadDir(base)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 || entries[0].Name() != "offline" {
		t.Fatalf("owned staging leaked: %v", entries)
	}
}

func TestCheckedGroupFirstInstallCreatesTrustedBase(t *testing.T) {
	parent := t.TempDir()
	base := filepath.Join(parent, "maps")
	name := "offline/0/0/0.000000_0.000000_0.200000_0.200000"
	archive := oneTile(t, name, "new")
	if err := installGroupArchive(context.Background(), clientFor(archive, 200), "https://synthetic.invalid/data", base, 0, 0); err != nil {
		t.Fatal(err)
	}
	if got := readTile(t, base, name); got != "new" {
		t.Fatalf("first install tile: %q", got)
	}
	for _, kind := range []string{"symlink", "file"} {
		t.Run(kind, func(t *testing.T) {
			blocked := filepath.Join(parent, kind)
			if kind == "symlink" {
				if err := os.Symlink(base, blocked); err != nil {
					t.Fatal(err)
				}
			} else if err := os.WriteFile(blocked, []byte("file"), 0644); err != nil {
				t.Fatal(err)
			}
			if err := installGroupArchive(context.Background(), clientFor(archive, 200), "https://synthetic.invalid/data", blocked, 0, 0); err == nil {
				t.Fatal("accepted symlink or nondirectory base")
			}
		})
	}
}

func TestCheckedGroupRejectsExistingSymlinkPaths(t *testing.T) {
	for _, kind := range []string{"parent", "target"} {
		t.Run(kind, func(t *testing.T) {
			base, name := setupExisting(t)
			other := t.TempDir()
			if kind == "parent" {
				if err := os.RemoveAll(filepath.Join(base, "offline/0/0")); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink(other, filepath.Join(base, "offline/0/0")); err != nil {
					t.Fatal(err)
				}
			} else {
				if err := os.Remove(filepath.Join(base, name)); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink(filepath.Join(other, "escaped"), filepath.Join(base, name)); err != nil {
					t.Fatal(err)
				}
			}
			err := installGroupArchive(context.Background(), clientFor(oneTile(t, name, "new"), 200), "https://synthetic.invalid/data", base, 0, 0)
			if err == nil {
				t.Fatal("accepted existing symlink")
			}
			if _, statErr := os.Stat(filepath.Join(other, "escaped")); !os.IsNotExist(statErr) {
				t.Fatalf("escaped: %v", statErr)
			}
		})
	}
}

type closeFailBody struct{ *bytes.Reader }

func (b closeFailBody) Close() error { return errors.New("body close failed") }

type readFailBody struct{}

func (readFailBody) Read([]byte) (int, error) { return 0, errors.New("body read failed") }
func (readFailBody) Close() error             { return nil }
func TestDownloadFileDoesNotTruncateOnHTTPOrBodyFailure(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "archive")
	if err := os.WriteFile(target, []byte("existing"), 0644); err != nil {
		t.Fatal(err)
	}
	for _, client := range []*http.Client{
		clientFor(nil, 503),
		{Transport: archiveTransport{status: 200, responseBody: closeFailBody{bytes.NewReader([]byte("new"))}}},
		{Transport: archiveTransport{status: 200, responseBody: readFailBody{}}},
	} {
		if err := downloadFile(context.Background(), client, "https://synthetic.invalid/data", target); err == nil {
			t.Fatal("expected error")
		}
		b, _ := os.ReadFile(target)
		if string(b) != "existing" {
			t.Fatalf("truncated existing: %q", b)
		}
	}
}

type waitTransport struct{}

func (waitTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	<-req.Context().Done()
	return nil, req.Context().Err()
}
func TestDownloadBoundsCancellationAndProgressSnapshot(t *testing.T) {
	base := t.TempDir()
	// Exercise the actual install function with canceled request, without touching global params.
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		done <- installGroupArchive(ctx, &http.Client{Transport: waitTransport{}}, "https://synthetic.invalid/data", base, 0, 0)
	}()
	cancel()
	select {
	case err := <-done:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("want cancellation: %v", err)
		}
	case <-time.After(time.Second):
		t.Fatal("cancellation hung")
	}
	d := download{progress: DownloadProgress{LocationsToDownload: []string{"a"}, LocationDetails: map[string]*DownloadLocationDetail{"a": {DownloadedFiles: 1}}}, progressChan: make(chan DownloadProgress, 2)}
	d.reportProgress()
	snapshot := <-d.progressChan
	d.progress.LocationDetails["a"].DownloadedFiles = 2
	d.progress.LocationsToDownload[0] = "b"
	if snapshot.LocationDetails["a"].DownloadedFiles != 1 || snapshot.LocationsToDownload[0] != "a" {
		t.Fatal("progress snapshot shared mutable storage")
	}
	if entries, err := os.ReadDir(base); err != nil || len(entries) != 0 {
		t.Fatalf("canceled stage not cleaned: %v %v", entries, err)
	}
}

func TestCheckedMemberRejectsPathAndTypes(t *testing.T) {
	for _, n := range []string{"../sentinel", "offline/0/0/../tile", "offline/0/0//tile", "offline/0/0/child/tile", "offline/2/0/tile", "/offline/0/0/tile", "offline\\0\\0\\tile"} {
		if _, err := checkedMember(n, tar.TypeReg, "offline/0/0"); err == nil {
			t.Fatalf("accepted %q", n)
		}
	}
	if _, err := checkedMember("offline/0/0/tile", tar.TypeLink, "offline/0/0"); err == nil {
		t.Fatal("accepted hardlink")
	}
	if _, err := checkedMember("offline/0/0/tile", tar.TypeReg, "offline/0/0"); err != nil {
		t.Fatal(err)
	}
}

type firstThenWaitTransport struct {
	first    []byte
	started  chan struct{}
	requests atomic.Int32
}

func (t *firstThenWaitTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if t.requests.Add(1) == 1 {
		return archiveTransport{body: t.first, status: 200}.RoundTrip(req)
	}
	close(t.started)
	<-req.Context().Done()
	return nil, req.Context().Err()
}

func TestDownloadBoundsCountsOnlyInstalledGroupsAndCancelsNext(t *testing.T) {
	base := t.TempDir()
	name := "offline/0/0/0.000000_0.000000_0.200000_0.200000"
	transport := &firstThenWaitTransport{first: oneTile(t, name, "first"), started: make(chan struct{})}
	d := download{
		progress:     DownloadProgress{LocationDetails: map[string]*DownloadLocationDetail{"test": {}}},
		progressChan: make(chan DownloadProgress, 4), cancelChan: make(chan bool, 1),
		client: &http.Client{Transport: transport}, basePath: base,
	}
	done := make(chan struct {
		err    error
		cancel bool
	}, 1)
	go func() {
		err, canceled := d.downloadBounds(Bounds{MinLat: 0, MinLon: 0, MaxLat: 2.1, MaxLon: 0.1}, "test")
		done <- struct {
			err    error
			cancel bool
		}{err, canceled}
	}()
	select {
	case <-transport.started:
	case <-time.After(time.Second):
		t.Fatal("second request did not start")
	}
	d.cancelChan <- true
	select {
	case result := <-done:
		if !result.cancel || result.err != nil {
			t.Fatalf("cancel result: %+v", result)
		}
	case <-time.After(time.Second):
		t.Fatal("cancellation hung")
	}
	if d.progress.DownloadedFiles != 1 || d.progress.LocationDetails["test"].DownloadedFiles != 1 {
		t.Fatalf("incorrect progress: %+v", d.progress)
	}
	if got := readTile(t, base, name); got != "first" {
		t.Fatalf("completed group lost: %q", got)
	}
	if _, err := os.Stat(filepath.Join(base, "offline/2")); !os.IsNotExist(err) {
		t.Fatalf("canceled group installed: %v", err)
	}
}
