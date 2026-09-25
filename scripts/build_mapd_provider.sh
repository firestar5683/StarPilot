#!/usr/bin/env bash
# Explicit, offline Linux/ARM64 Go package for the opt-in Mapd shadow owner.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
OUTPUT_DIR="${ROOT_DIR}/openpilot/starpilot/maps/provider"
MODULE_CACHE="${COMMA_MAPD_MODULE_CACHE:-${ROOT_DIR}/.cache/mapd-go-modules}"
BUILD_CACHE="${COMMA_MAPD_BUILD_CACHE:-${ROOT_DIR}/.cache/mapd-go-build}"
IMAGE="${COMMA_MAPD_BUILD_IMAGE:-openpilot-local-mapd-builder:go1.25.1}"

if [[ $# -ne 0 ]]; then
  echo 'ERROR: build_mapd_provider.sh takes no arguments; use ./build --mapd' >&2
  exit 2
fi

if [[ "${MODULE_CACHE}" != /* ]]; then MODULE_CACHE="${ROOT_DIR}/${MODULE_CACHE}"; fi
if [[ "${BUILD_CACHE}" != /* ]]; then BUILD_CACHE="${ROOT_DIR}/${BUILD_CACHE}"; fi

if [[ ! -d "${MODULE_CACHE}" ]]; then
  echo "ERROR: offline Go module cache missing: ${MODULE_CACHE}" >&2
  echo 'Prepare it explicitly from mapd_repo/go.mod and go.sum with Go 1.25.1, then set COMMA_MAPD_MODULE_CACHE.' >&2
  exit 1
fi

# Only a direct child of the checkout's ignored cache may be written. Check
# before mkdir so a misplaced override never creates files in another tree.
[[ "$(dirname "${BUILD_CACHE}")" == "${ROOT_DIR}/.cache" &&
   "$(basename "${BUILD_CACHE}")" != . && "$(basename "${BUILD_CACHE}")" != .. ]] || {
  echo 'ERROR: COMMA_MAPD_BUILD_CACHE must resolve beneath this checkout .cache' >&2
  exit 1
}
[[ ! -L "${ROOT_DIR}/.cache" && ! -L "${BUILD_CACHE}" && ! -L "${OUTPUT_DIR}" ]] || {
  echo 'ERROR: Mapd build cache or output cannot be a symlink' >&2
  exit 1
}
[[ "$(cd "$(dirname "${OUTPUT_DIR}")" && pwd -P)" == "${ROOT_DIR}/openpilot/starpilot/maps" ]] || {
  echo 'ERROR: Mapd provider parent resolves outside checkout' >&2
  exit 1
}
mkdir -p "${ROOT_DIR}/.cache" "${BUILD_CACHE}" "${OUTPUT_DIR}"
[[ "$(cd "${BUILD_CACHE}" && pwd -P)" == "${ROOT_DIR}/.cache/"* ]] || {
  echo 'ERROR: Mapd build cache resolves outside checkout' >&2
  exit 1
}
[[ "$(cd "${OUTPUT_DIR}" && pwd -P)" == "${ROOT_DIR}/openpilot/starpilot/maps/provider" ]] || {
  echo 'ERROR: Mapd package output directory must remain inside this checkout' >&2
  exit 1
}
MODULE_CACHE="$(cd "${MODULE_CACHE}" && pwd -P)"

if [[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]]; then
  GO="${COMMA_MAPD_GO:-$(command -v go || true)}"
  [[ -n "${GO}" ]] || { echo 'ERROR: explicit Go 1.25.1 toolchain required' >&2; exit 1; }
  cd "${ROOT_DIR}"
  GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off GOMODCACHE="${MODULE_CACHE}" GOCACHE="${BUILD_CACHE}" \
    python3 -m openpilot.starpilot.maps.package_shadow --go "${GO}" --output "${OUTPUT_DIR}"
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  ENGINE=docker
elif command -v podman >/dev/null 2>&1; then
  ENGINE=podman
else
  echo 'ERROR: Linux/ARM64 Docker or Podman is required for ./build --mapd on this host' >&2
  exit 1
fi
if ! "${ENGINE}" image inspect "${IMAGE}" >/dev/null 2>&1; then
  echo "ERROR: pinned Mapd builder image ${IMAGE} is absent" >&2
  echo 'Build it explicitly from tools/laptop_device_build/Dockerfile.mapd; this command never downloads images.' >&2
  exit 1
fi
ARCH="$("${ENGINE}" image inspect --format '{{.Os}}/{{.Architecture}}' "${IMAGE}")"
[[ "${ARCH}" == linux/arm64 ]] || { echo "ERROR: Mapd builder image is ${ARCH}, expected linux/arm64" >&2; exit 1; }

# Git worktrees have a .git pointer to an external common object directory.
# Mount that metadata read-only at its original path for package_shadow's
# exact HEAD stamp; the original checkout is never a writable build input.
git_common="$(git -C "${ROOT_DIR}" rev-parse --path-format=absolute --git-common-dir)"
[[ -d "${git_common}" ]] || { echo 'ERROR: checkout Git metadata unavailable' >&2; exit 1; }

"${ENGINE}" run --rm --pull=never --platform linux/arm64 --network none --read-only \
  --tmpfs /tmp:exec,size=2g --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=${ROOT_DIR},dst=/work,readonly" \
  --mount "type=bind,src=${OUTPUT_DIR},dst=/work/openpilot/starpilot/maps/provider" \
  --mount "type=bind,src=${MODULE_CACHE},dst=/gomodcache,readonly" \
  --mount "type=bind,src=${BUILD_CACHE},dst=/gocache" \
  --mount "type=bind,src=${git_common},dst=${git_common},readonly" \
  -e GOTOOLCHAIN=local -e GOPROXY=off -e GOSUMDB=off -e GOMODCACHE=/gomodcache \
  -e GOCACHE=/gocache -e GOPATH=/tmp/gopath -e PYTHONDONTWRITEBYTECODE=1 \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/work \
  -w /work --entrypoint python3 "${IMAGE}" -m openpilot.starpilot.maps.package_shadow \
  --go /usr/local/go/bin/go --output /work/openpilot/starpilot/maps/provider
