package settings

import (
	"archive/tar"
	"bufio"
	"compress/gzip"
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// A deadline bounds a stalled request without imposing an unsupported tile-size limit.
const downloadTimeout = 10 * time.Minute

type contextReader struct {
	context.Context
	io.Reader
}

func (r contextReader) Read(p []byte) (int, error) {
	if err := r.Context.Err(); err != nil {
		return 0, err
	}
	return r.Reader.Read(p)
}

func downloadFile(ctx context.Context, client *http.Client, url, target string) (err error) {
	parent := filepath.Dir(target)
	staged, err := os.CreateTemp(parent, ".mapd-download-")
	if err != nil {
		return err
	}
	defer os.Remove(staged.Name())
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		staged.Close()
		return err
	}
	resp, err := client.Do(req)
	if err != nil {
		staged.Close()
		return err
	}
	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		staged.Close()
		return fmt.Errorf("download received bad status: %s", resp.Status)
	}
	copied, copyErr := io.Copy(staged, contextReader{ctx, resp.Body})
	closeBodyErr := resp.Body.Close()
	if copyErr == nil && resp.ContentLength >= 0 && copied != resp.ContentLength {
		copyErr = io.ErrUnexpectedEOF
	}
	syncErr := staged.Sync()
	closeErr := staged.Close()
	if err = errors.Join(copyErr, closeBodyErr, syncErr, closeErr, ctx.Err()); err != nil {
		return err
	}
	if err = os.Rename(staged.Name(), target); err != nil {
		return err
	}
	dir, err := os.Open(parent)
	if err != nil {
		return err
	}
	return errors.Join(dir.Sync(), dir.Close())
}

// installGroupArchive validates the complete archive before changing installed files.
// Each replacement is atomic; the whole group is not one transaction.
func installGroupArchive(ctx context.Context, client *http.Client, url, base string, lat, lon int) (err error) {
	if err = ensureTrustedBase(base); err != nil {
		return err
	}
	root, err := os.OpenRoot(base)
	if err != nil {
		return err
	}
	baseInfo, statErr := os.Lstat(base)
	rootInfo, rootErr := root.Stat(".")
	if statErr != nil || rootErr != nil || !baseInfo.IsDir() || baseInfo.Mode()&os.ModeSymlink != 0 || !os.SameFile(baseInfo, rootInfo) {
		root.Close()
		return fmt.Errorf("unsafe map base directory: %s", base)
	}
	defer func() { err = errors.Join(err, root.Close()) }()
	stage, err := os.MkdirTemp(base, ".mapd-install-")
	if err != nil {
		return err
	}
	stageName := filepath.Base(stage)
	defer func() { err = errors.Join(err, root.RemoveAll(stageName)) }()
	archive := filepath.Join(stage, "archive.tar.gz")
	if err = downloadFile(ctx, client, url, archive); err != nil {
		return err
	}
	group := fmt.Sprintf("offline/%d/%d", lat, lon)
	files, err := extractCheckedArchive(ctx, root, stageName, archive, group)
	if err != nil {
		return err
	}
	if err = ctx.Err(); err != nil {
		return err
	}
	if err = ensureGroupDirs(root, group); err != nil {
		return err
	}
	for _, member := range files {
		if err = ctx.Err(); err != nil {
			return err
		}
		info, statErr := root.Lstat(member)
		if statErr == nil && !info.Mode().IsRegular() {
			return fmt.Errorf("nonregular installed target: %s", member)
		}
		if statErr != nil && !os.IsNotExist(statErr) {
			return statErr
		}
		if err = root.Rename(path.Join(stageName, member), member); err != nil {
			return err
		}
	}
	dir, err := root.Open(group)
	if err != nil {
		return err
	}
	return errors.Join(dir.Sync(), dir.Close())
}

// ExtractGroupArchiveFile uses the same checked tar/gzip member parser as the
// downloader, but installs only into a caller-owned unpublished directory.
func ExtractGroupArchiveFile(ctx context.Context, archive, output string, lat, lon int) (err error) {
	return ExtractGroupArchiveFileLimited(ctx, archive, output, lat, lon, nil)
}

// ExtractGroupArchiveFileLimited charges each expanded member before writing
// it into the unpublished generation. A nil charge preserves the old API.
func ExtractGroupArchiveFileLimited(ctx context.Context, archive, output string, lat, lon int, charge func(int64) error) (err error) {
	root, err := os.OpenRoot(output)
	if err != nil {
		return err
	}
	defer func() { err = errors.Join(err, root.Close()) }()
	stage, err := os.MkdirTemp(output, ".mapd-archive-")
	if err != nil {
		return err
	}
	stageName := filepath.Base(stage)
	defer func() { err = errors.Join(err, root.RemoveAll(stageName)) }()
	group := fmt.Sprintf("offline/%d/%d", lat, lon)
	files, err := extractCheckedArchiveLimited(ctx, root, stageName, archive, group, charge)
	if err != nil {
		return err
	}
	for _, name := range files {
		if err = ctx.Err(); err != nil {
			return err
		}
		rel := strings.TrimPrefix(name, "offline/")
		if err = root.MkdirAll(path.Dir(rel), 0o700); err != nil {
			return err
		}
		if _, statErr := root.Lstat(rel); statErr == nil {
			return fmt.Errorf("duplicate snapshot tile: %s", rel)
		} else if !os.IsNotExist(statErr) {
			return statErr
		}
		if err = root.Rename(path.Join(stageName, name), rel); err != nil {
			return err
		}
	}
	return nil
}

func ensureTrustedBase(base string) error {
	if base == "" || !filepath.IsAbs(base) {
		return fmt.Errorf("map base must be an absolute path: %q", base)
	}
	info, err := os.Lstat(base)
	if os.IsNotExist(err) {
		if err = os.MkdirAll(base, 0o755); err != nil {
			return err
		}
		info, err = os.Lstat(base)
	}
	if err != nil {
		return err
	}
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("unsafe map base directory: %s", base)
	}
	return nil
}

func ensureGroupDirs(root *os.Root, group string) error {
	parts := strings.Split(group, "/")
	for i := range parts {
		p := strings.Join(parts[:i+1], "/")
		info, err := root.Lstat(p)
		if os.IsNotExist(err) {
			if err = root.Mkdir(p, 0o755); err != nil {
				return err
			}
			info, err = root.Lstat(p)
		}
		if err != nil {
			return err
		}
		if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("unsafe installed directory: %s", p)
		}
	}
	return nil
}

func checkedMember(name string, typeflag byte, group string) (string, error) {
	normalized := name
	if typeflag == tar.TypeDir {
		normalized = strings.TrimSuffix(name, "/")
	}
	if normalized == "" || strings.HasPrefix(normalized, "/") || strings.ContainsAny(normalized, "\\\x00") || path.Clean(normalized) != normalized {
		return "", fmt.Errorf("unsafe archive path: %q", name)
	}
	if typeflag == tar.TypeDir {
		if normalized == "offline" || normalized == path.Dir(group) || normalized == group {
			return normalized, nil
		}
		return "", fmt.Errorf("unexpected archive directory: %q", name)
	}
	if typeflag != tar.TypeReg {
		return "", fmt.Errorf("unsupported archive entry: %q type %d", name, typeflag)
	}
	if path.Dir(normalized) != group || path.Base(normalized) == "." {
		return "", fmt.Errorf("archive member outside requested group: %q", name)
	}
	return normalized, nil
}

func extractCheckedArchive(ctx context.Context, root *os.Root, stageName, archive, group string) (files []string, err error) {
	return extractCheckedArchiveLimited(ctx, root, stageName, archive, group, nil)
}

func extractCheckedArchiveLimited(ctx context.Context, root *os.Root, stageName, archive, group string, charge func(int64) error) (files []string, err error) {
	fd, err := syscall.Open(archive, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return nil, err
	}
	file := os.NewFile(uintptr(fd), archive)
	defer func() { err = errors.Join(err, file.Close()) }()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		return nil, errors.New("archive must be a regular file")
	}
	buffered := bufio.NewReader(file)
	gz, err := gzip.NewReader(buffered)
	if err != nil {
		return nil, err
	}
	gz.Multistream(false)
	defer func() { err = errors.Join(err, gz.Close()) }()
	tr := tar.NewReader(contextReader{ctx, gz})
	seen := make(map[string]bool)
	for {
		header, nextErr := tr.Next()
		if nextErr == io.EOF {
			break
		}
		if nextErr != nil {
			return nil, nextErr
		}
		if header == nil {
			return nil, errors.New("nil tar header")
		}
		member, checkErr := checkedMember(header.Name, header.Typeflag, group)
		if checkErr != nil {
			return nil, checkErr
		}
		if seen[member] {
			return nil, fmt.Errorf("duplicate archive member: %s", member)
		}
		seen[member] = true
		if header.Typeflag == tar.TypeDir {
			continue
		}
		if charge != nil {
			if chargeErr := charge(header.Size); chargeErr != nil {
				return nil, chargeErr
			}
		}
		dest := path.Join(stageName, member)
		if mkdirErr := root.MkdirAll(path.Dir(dest), 0o700); mkdirErr != nil {
			return nil, mkdirErr
		}
		out, openErr := root.OpenFile(dest, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
		if openErr != nil {
			return nil, openErr
		}
		copied, copyErr := io.CopyN(out, tr, header.Size)
		if copyErr == nil && copied != header.Size {
			copyErr = io.ErrUnexpectedEOF
		}
		syncErr := out.Sync()
		closeErr := out.Close()
		if joined := errors.Join(copyErr, syncErr, closeErr); joined != nil {
			return nil, joined
		}
		files = append(files, member)
	}
	if len(files) == 0 {
		return nil, errors.New("archive contains no map files")
	}
	// tar.Reader stops at its first zero block. Require the rest of the tar stream
	// to be padding only, drain gzip to verify its footer, and reject extra members.
	padding := make([]byte, 32*1024)
	for {
		n, readErr := (contextReader{ctx, gz}).Read(padding)
		for _, b := range padding[:n] {
			if b != 0 {
				return nil, errors.New("unexpected content after tar end")
			}
		}
		if readErr == io.EOF {
			break
		}
		if readErr != nil {
			return nil, readErr
		}
	}
	if _, peekErr := buffered.Peek(1); peekErr != io.EOF {
		if peekErr == nil {
			return nil, errors.New("trailing compressed archive data")
		}
		return nil, peekErr
	}
	return files, nil
}
