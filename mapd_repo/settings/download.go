package settings

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math"
	"net/http"
	"os"
	"strings"
	"sync/atomic"

	"pfeifer.dev/mapd/params"
)

type LocationData struct {
	BoundingBox Bounds `json:"bounding_box"`
	FullName    string `json:"full_name"`
	Submenu     string `json:"submenu"`
}

type DownloadMenu map[string]map[string]LocationData

// BundledDownloadMenu is the immutable release catalog. Managed snapshot
// requests must not consult the legacy, locally overridable download menu.
func BundledDownloadMenu() (DownloadMenu, error) {
	var menu DownloadMenu
	if err := json.Unmarshal(boundingBoxesJson, &menu); err != nil {
		return nil, err
	}
	return menu, nil
}

func GetDownloadMenu() (menu DownloadMenu) {
	if _, err := os.Stat("/data/openpilot/mapd_download_menu.json"); err == nil {
		recommended, err := os.ReadFile("/data/openpilot/mapd_download_menu.json")
		if err != nil {
			slog.Warn("failed to read custom download menu", "error", err)
		}
		err = json.Unmarshal(recommended, &menu)
		if err != nil {
			slog.Warn("failed to load custom download menu", "error", err)
			return
		}
	} else {
		err := json.Unmarshal(boundingBoxesJson, &menu)
		if err != nil {
			slog.Warn("failed to load download menu", "error", err)
			return
		}
	}
	return
}

func DownloadFile(url string, filepath string) error {
	ctx, cancel := context.WithTimeout(context.Background(), downloadTimeout)
	defer cancel()
	return downloadFile(ctx, http.DefaultClient, url, filepath)
}

type Bounds struct {
	MinLat float64 `json:"min_lat"`
	MinLon float64 `json:"min_lon"`
	MaxLat float64 `json:"max_lat"`
	MaxLon float64 `json:"max_lon"`
}

type DownloadProgress struct {
	TotalFiles          int                                `json:"total_files"`
	DownloadedFiles     int                                `json:"downloaded_files"`
	Canceled            bool                               `json:"canceled"`
	Active              bool                               `json:"active"`
	LocationsToDownload []string                           `json:"locations_to_download"`
	LocationDetails     map[string]*DownloadLocationDetail `json:"location_details"`
}

type DownloadLocationDetail struct {
	TotalFiles      int `json:"location_total_files"`
	DownloadedFiles int `json:"location_downloaded_files"`
}

type download struct {
	progress     DownloadProgress
	progressChan chan DownloadProgress
	cancelChan   chan bool
	client       *http.Client
	basePath     string
}

func (d *download) reportProgress() {
	p := d.progress
	p.LocationsToDownload = append([]string(nil), p.LocationsToDownload...)
	p.LocationDetails = make(map[string]*DownloadLocationDetail, len(d.progress.LocationDetails))
	for name, detail := range d.progress.LocationDetails {
		copy := *detail
		p.LocationDetails[name] = &copy
	}
	select {
	case d.progressChan <- p:
	default:
	}
}

func (p *DownloadProgress) addLocationDetails(path string) {
	p.LocationDetails[path] = &DownloadLocationDetail{
		TotalFiles: countFilesForBounds(getBoundsForPath(path)),
	}
}

func Download(paths string, progressChan chan DownloadProgress, cancelChan chan bool) {
	slog.Info("download", "paths", paths)
	pathsSplit := strings.Split(paths, ",")
	d := download{
		progress: DownloadProgress{
			LocationsToDownload: pathsSplit,
			TotalFiles:          countTotalFiles(pathsSplit),
			LocationDetails:     make(map[string]*DownloadLocationDetail),
			Active:              true,
		},
		progressChan: progressChan,
		cancelChan:   cancelChan,
	}

	for _, p := range pathsSplit {
		d.progress.addLocationDetails(p)
		location := getDataForPath(p)
		slog.Info("downloading nation", "nation", location.FullName)
		err, canceled := d.downloadBounds(location.BoundingBox, p)
		if err != nil {
			slog.Warn("failed to download nation", "error", err, "nation", location.FullName)
		}
		if canceled {
			d.progress.Canceled = true
			break
		}
	}
	d.progress.Active = false
	d.reportProgress()
}

func adjustedBounds(bounds Bounds) (int, int, int, int) {
	minLat := int(math.Floor(bounds.MinLat/float64(GROUP_AREA_BOX_DEGREES))) * GROUP_AREA_BOX_DEGREES
	minLon := int(math.Floor(bounds.MinLon/float64(GROUP_AREA_BOX_DEGREES))) * GROUP_AREA_BOX_DEGREES
	maxLat := int(math.Floor(bounds.MaxLat/float64(GROUP_AREA_BOX_DEGREES))) * GROUP_AREA_BOX_DEGREES
	maxLon := int(math.Floor(bounds.MaxLon/float64(GROUP_AREA_BOX_DEGREES))) * GROUP_AREA_BOX_DEGREES

	if bounds.MaxLat > float64(maxLat) {
		maxLat += GROUP_AREA_BOX_DEGREES
	}
	if bounds.MaxLon > float64(maxLon) {
		maxLon += GROUP_AREA_BOX_DEGREES
	}
	return minLat, minLon, maxLat, maxLon
}

func (d *download) downloadBounds(bounds Bounds, locationName string) (error, bool) {
	slog.Info("Downloading Bounds", "min_lat", bounds.MinLat, "min_lon", bounds.MinLon, "max_lat", bounds.MaxLat, "max_lon", bounds.MaxLon)
	minLat, minLon, maxLat, maxLon := adjustedBounds(bounds)
	d.progress.LocationDetails[locationName].TotalFiles = countFilesForBounds(bounds)
	ctx, stop := context.WithCancel(context.Background())
	var canceled atomic.Bool
	done := make(chan struct{})
	go func() {
		defer close(done)
		for {
			select {
			case value, open := <-d.cancelChan:
				if !open || value {
					canceled.Store(true)
					stop()
					return
				}
			case <-ctx.Done():
				return
			}
		}
	}()
	defer func() { stop(); <-done }()
	client := d.client
	if client == nil {
		client = http.DefaultClient
	}
	base := d.basePath
	if base == "" {
		base = params.GetBaseOpPath()
	}
	var firstError error
	for i := minLat; i < maxLat; i += GROUP_AREA_BOX_DEGREES {
		for j := minLon; j < maxLon; j += GROUP_AREA_BOX_DEGREES {
			d.reportProgress()
			if canceled.Load() || ctx.Err() != nil {
				return firstError, true
			}
			url := fmt.Sprintf("https://map-data.pfeifer.dev/offline/%d/%d.tar.gz", i, j)
			requestCtx, requestStop := context.WithTimeout(ctx, downloadTimeout)
			installErr := installGroupArchive(requestCtx, client, url, base, i, j)
			requestStop()
			if installErr != nil {
				if canceled.Load() || ctx.Err() != nil {
					return firstError, true
				}
				if firstError == nil {
					firstError = installErr
				}
				slog.Warn("failed to install offline map group", "error", installErr, "url", url)
				continue
			}
			d.progress.DownloadedFiles++
			d.progress.LocationDetails[locationName].DownloadedFiles++
			if canceled.Load() || ctx.Err() != nil {
				return firstError, true
			}
		}
	}
	slog.Info("Finished Downloading Bounds", "min_lat", bounds.MinLat, "min_lon", bounds.MinLon, "max_lat", bounds.MaxLat, "max_lon", bounds.MaxLon)
	return firstError, false
}

func countFilesForBounds(bounds Bounds) int {
	minLat, minLon, maxLat, maxLon := adjustedBounds(bounds)
	return ((maxLat - minLat) / GROUP_AREA_BOX_DEGREES) * ((maxLon - minLon) / GROUP_AREA_BOX_DEGREES)
}

func getDataForPath(path string) LocationData {
	parts := strings.Split(path, ".")
	if len(parts) < 2 {
		slog.Warn("ignoring invalid download path", "path", path)
		return LocationData{}
	}
	menu := GetDownloadMenu()
	box := menu[parts[0]][parts[1]]
	if len(parts) > 2 {
		for i := range len(parts) - 2 {
			box = menu[box.Submenu][parts[i+2]]
		}
	}
	return box
}

func getBoundsForPath(path string) Bounds {
	return getDataForPath(path).BoundingBox
}

func countTotalFiles(paths []string) int {
	totalFiles := 0

	for _, p := range paths {
		totalFiles += countFilesForBounds(getBoundsForPath(p))
	}

	return totalFiles
}
