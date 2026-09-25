package maps

import (
	"context"
	"errors"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

const snapshotArchiveOrigin = "https://map-data.pfeifer.dev"
const snapshotFetchTimeout = 10 * time.Minute
const snapshotFetchOperationTimeout = 30 * time.Minute
const snapshotFetchAttempts = 3

var errSnapshotDiskWrite = errors.New("snapshot archive staging write failed")

const SnapshotAttributionNotice = attribution

type FetchOptions struct {
	AdmitOptions
	MaxBytes        int64 // total transferred archive bytes, across every group
	MaxNewDiskBytes int64 // managed staging writes; zero preserves direct CLI behavior
	PrepareOnly     bool
	Progress        func(FetchProgress) error
}

type FetchProgress struct {
	Phase          string `json:"phase"`
	Completed      int    `json:"completedGroups"`
	Total          int    `json:"totalGroups"`
	Transferred    int64  `json:"transferredBytes"`
	TransferBudget int64  `json:"transferBudgetBytes"`
}

type chargedWriter struct {
	w      io.Writer
	budget *SnapshotDiskBudget
}

func (w chargedWriter) Write(data []byte) (int, error) {
	if err := w.budget.charge(int64(len(data))); err != nil {
		return 0, err
	}
	n, err := w.w.Write(data)
	if err != nil || n != len(data) {
		if err == nil {
			err = io.ErrShortWrite
		}
		return n, fmt.Errorf("%w: %v", errSnapshotDiskWrite, err)
	}
	return n, nil
}

func snapshotFetchClient(client *http.Client) *http.Client {
	if client == nil {
		client = http.DefaultClient
	}
	copy := *client
	if copy.Timeout == 0 || copy.Timeout > snapshotFetchTimeout {
		copy.Timeout = snapshotFetchTimeout
	}
	previous := copy.CheckRedirect
	copy.CheckRedirect = func(req *http.Request, via []*http.Request) error {
		if len(via) > 3 || req.URL.Scheme != "https" || req.URL.Host != "map-data.pfeifer.dev" || req.URL.User != nil {
			return errors.New("snapshot archive redirect left the fixed origin")
		}
		if previous != nil {
			return previous(req, via)
		}
		return nil
	}
	return &copy
}

// The returned byte count includes failed attempts. Callers must charge it to
// the global transfer cap even when a retry eventually succeeds.
func fetchSnapshotArchive(ctx context.Context, client *http.Client, stage string, lat, lon int, remaining int64, budget *SnapshotDiskBudget) (int64, error) {
	var transferred int64
	for attempt := 0; attempt < snapshotFetchAttempts; attempt++ {
		if err := ctx.Err(); err != nil {
			return transferred, err
		}
		if remaining-transferred <= 0 {
			return transferred, errors.New("snapshot archive transfer budget exhausted")
		}
		n, retryable, err := fetchSnapshotArchiveOnce(ctx, client, stage, lat, lon, remaining-transferred, budget)
		transferred += n
		if err == nil || !retryable || attempt+1 == snapshotFetchAttempts {
			return transferred, err
		}
		wait := time.NewTimer(time.Duration(attempt+1) * 100 * time.Millisecond)
		select {
		case <-ctx.Done():
			wait.Stop()
			return transferred, ctx.Err()
		case <-wait.C:
		}
	}
	return transferred, errors.New("snapshot archive retry exhausted")
}

func fetchSnapshotArchiveOnce(ctx context.Context, client *http.Client, stage string, lat, lon int, remaining int64, budget *SnapshotDiskBudget) (n int64, retryable bool, err error) {
	urlText := snapshotArchiveOrigin + "/offline/" + strconv.Itoa(lat) + "/" + strconv.Itoa(lon) + ".tar.gz"
	parsed, err := url.Parse(urlText)
	if err != nil || parsed.Scheme != "https" || parsed.Host != "map-data.pfeifer.dev" {
		return 0, false, errors.New("invalid fixed archive URL")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, urlText, nil)
	if err != nil {
		return 0, false, err
	}
	req.Header.Set("Accept-Encoding", "identity")
	resp, err := client.Do(req)
	if err != nil {
		return 0, ctx.Err() == nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK || (resp.Header.Get("Content-Encoding") != "" && resp.Header.Get("Content-Encoding") != "identity") {
		return 0, resp.StatusCode == http.StatusRequestTimeout || resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500,
			fmt.Errorf("snapshot archive response rejected: status=%d encoding=%q", resp.StatusCode, resp.Header.Get("Content-Encoding"))
	}
	if resp.ContentLength > remaining {
		return 0, false, errors.New("snapshot archive exceeds remaining transfer budget")
	}
	path := filepath.Join(stage, strconv.Itoa(lat), strconv.Itoa(lon)+".tar.gz")
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return 0, false, err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return 0, false, err
	}
	defer func() {
		if err != nil {
			_ = os.Remove(path)
		}
	}()
	n, copyErr := io.Copy(chargedWriter{file, budget}, io.LimitReader(resp.Body, remaining+1))
	closeBodyErr := resp.Body.Close()
	syncErr := file.Sync()
	closeErr := file.Close()
	if err := errors.Join(copyErr, closeBodyErr, syncErr, closeErr, ctx.Err()); err != nil {
		bodyFailure := (copyErr != nil && !errors.Is(copyErr, ErrSnapshotDiskBudget) && !errors.Is(copyErr, errSnapshotDiskWrite)) || closeBodyErr != nil
		return n, bodyFailure && syncErr == nil && closeErr == nil && ctx.Err() == nil, err
	}
	if n > remaining {
		return n, false, errors.New("snapshot archive transfer exceeded budget")
	}
	if resp.ContentLength >= 0 && n != resp.ContentLength {
		return n, true, errors.New("snapshot archive transfer ended short")
	}
	return n, false, nil
}

// FetchAndAdmitSnapshot is an explicit development import path. The remote
// archive bytes are unverified source claims; only their observed hashes and
// locally validated tile content enter the snapshot receipt.
func FetchAndAdmitSnapshot(ctx context.Context, o FetchOptions, client *http.Client) (string, error) {
	ctx, stop := context.WithTimeout(ctx, snapshotFetchOperationTimeout)
	defer stop()
	if o.MaxBytes <= 0 || o.MaxBytes >= math.MaxInt64 {
		return "", errors.New("invalid total archive transfer budget")
	}
	if _, err := expectedSnapshotTiles(o.Bounds); err != nil {
		return "", err
	}
	if math.IsNaN(o.Overlap) || math.IsInf(o.Overlap, 0) || o.Overlap < 0 || o.Overlap >= 0.25 {
		return "", errors.New("invalid snapshot overlap")
	}
	for _, bound := range o.Bounds {
		if bound/2 != math.Round(bound/2) {
			return "", errors.New("archive region must align to two-degree groups")
		}
	}
	if err := ownedSnapshotDir(o.Root); err != nil {
		return "", err
	}
	var budget *SnapshotDiskBudget
	if o.MaxNewDiskBytes != 0 {
		bounded, budgetErr := NewSnapshotDiskBudget(o.Root, o.MaxNewDiskBytes)
		if budgetErr != nil {
			return "", budgetErr
		}
		budget = bounded
	}
	stage, err := os.MkdirTemp(o.Root, ".snapshot-fetch-")
	if err != nil {
		return "", err
	}
	defer os.RemoveAll(stage)
	boundedClient := snapshotFetchClient(client)
	var transferred int64
	total := int((o.Bounds[2] - o.Bounds[0]) / 2 * (o.Bounds[3] - o.Bounds[1]) / 2)
	report := func(phase string, completed int) error {
		if o.Progress != nil {
			return o.Progress(FetchProgress{Phase: phase, Completed: completed, Total: total,
				Transferred: transferred, TransferBudget: o.MaxBytes})
		}
		return nil
	}
	if err := report("transferring", 0); err != nil {
		return "", err
	}
	completed := 0
	for lat := int(o.Bounds[0]); lat < int(o.Bounds[2]); lat += 2 {
		for lon := int(o.Bounds[1]); lon < int(o.Bounds[3]); lon += 2 {
			if err := ctx.Err(); err != nil {
				return "", err
			}
			n, err := fetchSnapshotArchive(ctx, boundedClient, stage, lat, lon, o.MaxBytes-transferred, budget)
			transferred += n
			if err != nil {
				return "", err
			}
			completed++
			if err := report("transferring", completed); err != nil {
				return "", err
			}
		}
	}
	o.AdmitOptions.PBF = ""
	o.AdmitOptions.ArchiveDir = stage
	o.AdmitOptions.SourceURL = snapshotArchiveOrigin + "/offline/"
	o.AdmitOptions.SourceDate = ""
	o.AdmitOptions.Budget = budget
	if err := report("validating", completed); err != nil {
		return "", err
	}
	if o.PrepareOnly {
		return PrepareSnapshot(ctx, o.AdmitOptions)
	}
	return AdmitSnapshot(ctx, o.AdmitOptions)
}
