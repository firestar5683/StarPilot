package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// The required host target launches only --shadow with a disposable IPC prefix
// and a synthetic packed tile. It does not start the normal provider path.
func TestShadowExecutableHostGpsIPC(t *testing.T) {
	if os.Getenv("STARPILOT_SHADOW_EXEC_REQUIRED") != "1" {
		t.Skip("host executable IPC runs in the required integration target")
	}
	python := os.Getenv("STARPILOT_PYTHON")
	if python == "" || !filepath.IsAbs(python) {
		t.Fatal("absolute STARPILOT_PYTHON required")
	}
	root := t.TempDir()
	binary := filepath.Join(root, "mapd-shadow")
	goBinary := filepath.Join(runtime.GOROOT(), "bin", "go")
	if _, err := os.Stat(goBinary); err != nil {
		t.Fatalf("outer test toolchain is unavailable: %v", err)
	}
	build := exec.Command(goBinary, "build", "-mod=readonly", "-o", binary, ".")
	build.Env = append(os.Environ(), "GOTOOLCHAIN=local", "GOPROXY=off", "GOSUMDB=off")
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("shadow test build: %v: %s", err, out)
	}
	if out, err := exec.Command(binary, "--snapshot-admit", "--offline-root", root).CombinedOutput(); err == nil {
		t.Fatalf("admission accepted missing input/bounds: %s", out)
	}
	admit := exec.Command(binary, "--snapshot-admit", "--offline-root", root,
		"--input-pbf", filepath.Join("testdata", "synthetic_snapshot.osm.pbf"),
		"--min-lat", "35", "--min-lon", "-98", "--max-lat", "35.25", "--max-lon", "-97.75")
	if out, err := admit.CombinedOutput(); err != nil {
		t.Fatalf("actual snapshot CLI rejected synthetic input: %v: %s", err, out)
	}
	script, err := filepath.Abs(filepath.Join("..", "openpilot", "starpilot", "maps", "tests", "shadow_executable_host.py"))
	if err != nil {
		t.Fatal(err)
	}
	command := exec.Command(python, script)
	command.Env = append(os.Environ(), "STARPILOT_SHADOW_BINARY="+binary, "STARPILOT_SHADOW_ROOT="+root)
	command.Dir = ".."
	out, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("actual host GPS -> Go shadow -> Python status failed: %v: %s", err, out)
	}
	var result map[string]any
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if err := json.Unmarshal([]byte(lines[len(lines)-1]), &result); err != nil {
		t.Fatalf("missing JSON proof: %v: %s", err, out)
	}
	for _, key := range []string{"external", "invalidEvent", "noFix", "oldGps", "internalFallback", "stale", "restarted", "ignoredInputs"} {
		if result[key] != true {
			t.Fatalf("missing %s proof: %s", key, out)
		}
	}
	fmt.Println(string(out))
}
