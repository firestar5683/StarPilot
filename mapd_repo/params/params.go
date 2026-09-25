package params

import (
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/pkg/errors"

	"github.com/gofrs/flock"
)

var (
	ParamsPath string = "/data/params/d"
	BasePath   string = GetBasePath()
)

func GetBaseOpPath() string {
	exists, err := Exists("/data/media/0")
	if err != nil {
		slog.Warn("could not check if /data/media/0 exists", "error", err)
	}
	if exists {
		return "/data/media/0/osm"
	} else {
		return "."
	}
}

// Params
var (
	LAST_GPS_POSITION = ParamPath("LastGPSPosition")
	MAPD_SETTINGS     = ParamPath("MapdSettings")
)

// exists returns whether the given file or directory exists
func Exists(path string) (bool, error) {
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, errors.Wrap(err, "could not check param file stats")
}

func GetBasePath() string {
	exists, err := Exists("/data/media/0")
	if err != nil {
		slog.Warn("could not check if /data/media/0 exists", "error", err)
	}
	if exists {
		return "/data/media/0/osm"
	} else {
		return "media/"
	}
}

func EnsureParamDirectories() {
	err := os.MkdirAll(ParamsPath, 0o775)
	if err != nil {
		slog.Warn("could not make params directory", "error", err, "directory", ParamsPath)
	}
}

func ResetParams() {
}

func IsString(data []byte) bool {
	for _, b := range data {
		if (b < 32 || b > 126) && !(b == 9 || b == 13 || b == 10) {
			return false
		}
	}
	return true
}

func GetParams() ([]string, error) {
	basePath := ParamsPath

	files, err := os.ReadDir(basePath)
	if err != nil {
		return nil, errors.Wrap(err, "could not read params directory")
	}

	paramFiles := []string{}
	for _, file := range files {
		name := file.Name()
		if file.Type().IsRegular() && name[0] != '.' {
			paramFiles = append(paramFiles, name)
		}
	}
	sort.Strings(paramFiles)

	return paramFiles, nil
}

func ParamPath(name string) string {
	var basePath string
	basePath = ParamsPath
	return filepath.Join(basePath, name)
}

func GetParam(path string) ([]byte, error) {
	return os.ReadFile(path)
}

func PutParam(path string, data []byte) error {
	dir := filepath.Dir(path)
	lock_dir := filepath.Dir(dir)
	file, err := os.CreateTemp(dir, ".tmp_value_"+filepath.Base(path))
	if err != nil {
		return errors.Wrap(err, "could not create temp param file")
	}
	tmpName := file.Name()
	defer os.Remove(tmpName)

	_, err = file.Write(data)
	if err != nil {
		return errors.Wrap(err, "could not write data to temp param file")
	}

	err = file.Sync()
	if err != nil {
		return errors.Wrap(err, "could not fsync temp param file")
	}

	fileLock := flock.New(filepath.Join(lock_dir, ".lock"))

	retries := 0
	for {
		locked, err := fileLock.TryLock()
		if err != nil {
			return errors.Wrap(err, "could not try locking param directory")
		}
		if locked {
			break
		}
		retries += 1
		if retries > 30 {
			// try to force the lock to be removed
			if err := os.Remove(filepath.Join(lock_dir, ".lock")); err != nil {
				slog.Debug("failed to force delete params lock", "error", err)
			}
		}
		if retries > 50 {
			return errors.New("could not obtain lock")
		}
		// if we didn't obtain the lock let's try again after a short delay
		time.Sleep(1 * time.Millisecond)
	}
	defer func() {
		if err := fileLock.Unlock(); err != nil {
			slog.Error("could not unlock params directory", "error", err)
		}
	}()
	defer func() {
		if err := os.Remove(filepath.Join(lock_dir, ".lock")); err != nil {
			slog.Error("could not remove params lock file", "error", err)
		}
	}()

	err = os.Rename(tmpName, path)
	if err != nil {
		return errors.Wrap(err, "could not move temp param file to persistent location")
	}

	directory, err := os.Open(dir)
	if err != nil {
		return errors.Wrap(err, "could not open params directory")
	}

	err = directory.Sync()
	if err != nil {
		return errors.Wrap(err, "could not fsync params directory")
	}

	return nil
}

func RemoveParam(path string) error {
	dir := filepath.Dir(path)
	lock_dir := filepath.Dir(dir)
	fileLock := flock.New(filepath.Join(lock_dir, ".lock"))

	retries := 0
	for {
		locked, err := fileLock.TryLock()
		if err != nil {
			return errors.Wrap(err, "could not try locking params directory")
		}
		if locked {
			break
		}
		retries += 1
		if retries > 30 {
			// try to force the lock to be removed
			if err := os.Remove(filepath.Join(lock_dir, ".lock")); err != nil {
				slog.Debug("failed to force delete params lock", "error", err)
			}
		}
		if retries > 50 {
			return errors.New("could not obtain lock")
		}
		// if we didn't obtain the lock let's try again after a short delay
		time.Sleep(1 * time.Millisecond)
	}
	defer func() {
		if err := fileLock.Unlock(); err != nil {
			slog.Error("could not unlock params directory", "error", err)
		}
	}()
	defer func() {
		if err := os.Remove(filepath.Join(lock_dir, ".lock")); err != nil {
			slog.Error("could not remove params lock file", "error", err)
		}
	}()

	os.Remove(path)

	directory, err := os.Open(dir)
	if err != nil {
		return errors.Wrap(err, "could not open params directory")
	}

	err = directory.Sync()
	if err != nil {
		return errors.Wrap(err, "could not fsync params directory")
	}

	return nil
}
