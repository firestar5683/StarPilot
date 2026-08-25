#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

HOST_ROOT_DIR="${COMMA_HOST_ROOT_DIR:-${ROOT_DIR}}"
DOCKER_RUN_USER="${COMMA_DOCKER_RUN_USER:-$(id -u):$(id -g)}"
HOST_VENV_DIR="${COMMA_HOST_VENV_DIR:-${HOST_ROOT_DIR}/.venv-linux-arm64}"

# Make Docker Desktop binaries discoverable (docker + credential helpers) even
# when the caller shell PATH is minimal.
if [[ -d /Applications/Docker.app/Contents/Resources/bin ]]; then
  export PATH="/Applications/Docker.app/Contents/Resources/bin:${PATH}"
fi

IMAGE_NAME="${COMMA_BUILD_IMAGE:-starpilot-larch64-builder:latest}"
SYSROOT_DIR_DEFAULT="${ROOT_DIR}/.comma_sysroot"
SYSROOT_DIR="${COMMA_SYSROOT_DIR:-${SYSROOT_DIR_DEFAULT}}"
HOST_SYSROOT_DIR="${COMMA_HOST_SYSROOT_DIR:-${SYSROOT_DIR}}"
HOST_CACHE_DIR="${COMMA_HOST_CACHE_DIR:-${HOST_ROOT_DIR}/.cache}"
HOST_DOCKERFILE_PATH="${COMMA_HOST_DOCKERFILE_PATH:-${HOST_ROOT_DIR}/tools/laptop_device_build/Dockerfile}"

usage() {
  cat <<'EOF'
Usage:
  scripts/laptop_device_build.sh doctor
  scripts/laptop_device_build.sh setup [device-host] [device-user] [ssh-port]
  scripts/laptop_device_build.sh setup-sysroot <device-host> [device-user] [ssh-port]
  scripts/laptop_device_build.sh setup-sysroot-agnos [manifest-path]
  scripts/laptop_device_build.sh build-image
  scripts/laptop_device_build.sh build [jobs] [scons args...]
  scripts/laptop_device_build.sh scons [--no-scrub] [scons args...]
  scripts/laptop_device_build.sh manager [jobs] [--no-build] [-- manager args...]
  scripts/laptop_device_build.sh shell

Modes:
  doctor        Check host/container prerequisites for laptop-side device builds.
  setup         One-time setup for laptop builds (venv + image + sysroot).
  setup-sysroot Sync required runtime/linker libs from a comma device over SSH.
  setup-sysroot-agnos Download AGNOS system image and extract sysroot locally.
  build-image   Build the Linux/aarch64 container image used for device-target builds.
  build         Run larch64 scons build in container and set prebuilt flag.
  scons         Run raw scons in the larch64 container (no prebuilt touch).
  manager       Run system/manager/manager.py in the larch64 container.
  shell         Open an interactive shell in the build container with all mounts.

Environment overrides:
  COMMA_BUILD_IMAGE   Container image tag (default: starpilot-larch64-builder:latest)
  COMMA_SYSROOT_DIR   Sysroot location (default: ./.comma_sysroot)
  COMMA_AUTOSTART_DOCKER  Auto-launch Docker Desktop on macOS when needed (default: 1)
EOF
}

err() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || err "Missing required command: $1"
}

detect_engine() {
  local docker_cmd=""
  if command -v docker >/dev/null 2>&1; then
    docker_cmd="$(command -v docker)"
  elif [[ -x /Applications/Docker.app/Contents/Resources/bin/docker ]]; then
    docker_cmd="/Applications/Docker.app/Contents/Resources/bin/docker"
  fi

  if [[ -n "${docker_cmd}" ]]; then
    # Needed for docker credential helpers (e.g. docker-credential-desktop).
    export PATH="$(dirname "${docker_cmd}"):${PATH}"
    if ! "${docker_cmd}" info >/dev/null 2>&1; then
      if [[ "$(uname -s)" == "Darwin" ]] && [[ "${COMMA_AUTOSTART_DOCKER:-1}" =~ ^(1|true|yes|on)$ ]]; then
        if [[ -d /Applications/Docker.app ]] && command -v open >/dev/null 2>&1; then
          echo "Docker daemon is not running. Launching Docker Desktop..." >&2
          open -g -a Docker >/dev/null 2>&1 || open -a Docker >/dev/null 2>&1 || true
          for ((i=0; i<300; i++)); do
            if "${docker_cmd}" info >/dev/null 2>&1; then
              break
            fi
            sleep 1
          done
        fi
      fi
      if ! "${docker_cmd}" info >/dev/null 2>&1; then
        err "Docker CLI found, but Docker daemon is not running. Start Docker Desktop (open -a Docker) and retry."
      fi
    fi
    echo "${docker_cmd}"
    return
  fi
  if command -v podman >/dev/null 2>&1; then
    local podman_cmd
    podman_cmd="$(command -v podman)"
    if ! "${podman_cmd}" info >/dev/null 2>&1; then
      err "Podman CLI found, but Podman service is not running."
    fi
    echo "${podman_cmd}"
    return
  fi
  err "No container runtime found (install docker or podman)."
}

build_container_image_cmd() {
  local engine="$1"
  shift

  if [[ "${engine##*/}" == "docker" ]] && "${engine}" buildx version >/dev/null 2>&1; then
    "${engine}" buildx build --load --platform linux/arm64 "$@"
    return
  fi

  "${engine}" build --pull --platform linux/arm64 "$@"
}

ensure_image_exists() {
  local engine="$1"
  if ! "${engine}" image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "Container image ${IMAGE_NAME} not found. Building it now..."
    build_container_image_cmd "${engine}" --pull -f "${HOST_DOCKERFILE_PATH}" -t "${IMAGE_NAME}" "${HOST_ROOT_DIR}"
  fi
  assert_image_arch "${engine}"
  ensure_image_capnp_version "${engine}"
}

assert_image_arch() {
  local engine="$1"
  local arch
  arch="$("${engine}" image inspect "${IMAGE_NAME}" --format '{{.Architecture}}' 2>/dev/null || true)"
  if [[ "${arch}" != "arm64" ]]; then
    err "Container image ${IMAGE_NAME} is '${arch:-unknown}', expected 'arm64'. Rebuild with: ${engine} build --pull --platform linux/arm64 -f tools/laptop_device_build/Dockerfile -t ${IMAGE_NAME} ."
  fi
}

expected_capnp_version() {
  if [[ -n "${COMMA_EXPECTED_CAPNP_VERSION:-}" ]]; then
    echo "${COMMA_EXPECTED_CAPNP_VERSION}"
    return
  fi

  local dockerfile_version=""
  dockerfile_version="$(sed -n 's/^ARG CAPNP_VERSION=\(.*\)$/\1/p' "${ROOT_DIR}/tools/laptop_device_build/Dockerfile" | head -n 1)"
  if [[ -n "${dockerfile_version}" ]]; then
    echo "${dockerfile_version}"
    return
  fi

  local header_path="${ROOT_DIR}/cereal/gen/cpp/custom.capnp.h"
  if [[ ! -f "${header_path}" ]]; then
    err "Unable to determine expected Cap'n Proto version. Set COMMA_EXPECTED_CAPNP_VERSION or restore tools/laptop_device_build/Dockerfile ARG CAPNP_VERSION."
  fi

  local raw_version=""
  raw_version="$(sed -n 's/^#elif CAPNP_VERSION != \([0-9][0-9]*\)$/\1/p' "${header_path}" | head -n 1)"
  [[ -n "${raw_version}" ]] || err "Unable to determine expected Cap'n Proto version from ${header_path}."

  local major=$(( raw_version / 1000000 ))
  local minor=$(( (raw_version / 1000) % 1000 ))
  local micro=$(( raw_version % 1000 ))
  echo "${major}.${minor}.${micro}"
}

image_capnp_version() {
  local engine="$1"
  local version_output=""

  version_output="$("${engine}" run --rm --platform linux/arm64 "${IMAGE_NAME}" capnp --version 2>&1 || true)"
  printf '%s\n' "${version_output}" \
    | sed -nE 's/.*version[[:space:]]+([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' \
    | head -n 1
}

ensure_image_capnp_version() {
  local engine="$1"
  local expected actual
  expected="$(expected_capnp_version)"
  actual="$(image_capnp_version "${engine}")"

  if [[ "${actual}" == "${expected}" ]]; then
    return
  fi

  echo "Container image ${IMAGE_NAME} has Cap'n Proto ${actual:-unknown}, expected ${expected}. Rebuilding it now..."
  build_container_image_cmd "${engine}" --pull -f "${HOST_DOCKERFILE_PATH}" -t "${IMAGE_NAME}" "${HOST_ROOT_DIR}"

  actual="$(image_capnp_version "${engine}")"
  if [[ "${actual}" != "${expected}" ]]; then
    err "Container image ${IMAGE_NAME} still has Cap'n Proto ${actual:-unknown} after rebuild; expected ${expected}."
  fi
}

assert_runtime_machine() {
  local engine="$1"
  local machine
  machine="$("${engine}" run --rm --platform linux/arm64 "${IMAGE_NAME}" bash -lc "readelf -h \$(command -v python3) | awk -F: '/Machine/ {gsub(/^ +/, \"\", \$2); print \$2}'" 2>/dev/null || true)"
  if [[ "${machine}" != "AArch64" ]]; then
    err "Container Python runtime is '${machine:-unknown}', expected 'AArch64'. This image can still build device artifacts, but cannot run manager with larch64 Python extensions. Rebuild from an arm64-capable base image before using 'manager' mode."
  fi
}

default_jobs() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  elif command -v sysctl >/dev/null 2>&1; then
    sysctl -n hw.ncpu
  else
    echo 8
  fi
}

build_container_image() {
  local engine
  engine="$(detect_engine)"
  build_container_image_cmd "${engine}" --pull \
    -f "${HOST_DOCKERFILE_PATH}" \
    -t "${IMAGE_NAME}" "${HOST_ROOT_DIR}"
  assert_image_arch "${engine}"
}

sanitize_sysroot_headers() {
  # Device /usr/local/include can include older capnp/kj headers that conflict
  # with generated cereal headers in this tree. Keep ffmpeg headers, drop capnp.
  local removed=0
  local path=""
  for path in \
    "${SYSROOT_DIR}/usr/local/include/capnp" \
    "${SYSROOT_DIR}/usr/local/include/kj"; do
    if [[ -e "${path}" ]]; then
      rm -rf "${path}"
      removed=1
    fi
  done
  if [[ "${removed}" -eq 1 ]]; then
    echo "Sanitized sysroot headers: removed capnp/kj from usr/local/include"
  fi
}

ensure_sysroot_layout() {
  [[ -d "${SYSROOT_DIR}/usr/local/lib" ]] || err "Missing ${SYSROOT_DIR}/usr/local/lib. Run setup-sysroot first."
  [[ -d "${SYSROOT_DIR}/usr/local/include" ]] || err "Missing ${SYSROOT_DIR}/usr/local/include. Run setup-sysroot first."
  [[ -d "${SYSROOT_DIR}/lib/aarch64-linux-gnu" ]] || err "Missing ${SYSROOT_DIR}/lib/aarch64-linux-gnu. Run setup-sysroot first."
  [[ -d "${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu" ]] || err "Missing ${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu. Run setup-sysroot first."
  [[ -d "${SYSROOT_DIR}/usr/include" ]] || err "Missing ${SYSROOT_DIR}/usr/include. Run setup-sysroot first."
  [[ -d "${SYSROOT_DIR}/system/vendor/lib64" ]] || err "Missing ${SYSROOT_DIR}/system/vendor/lib64. Run setup-sysroot first."
  sanitize_sysroot_headers
  repair_sysroot_linker
}

is_aarch64_elf() {
  local path="${1:-}"
  [[ -f "${path}" ]] || return 1
  local desc
  desc="$(file -b "${path}" 2>/dev/null || true)"
  [[ "${desc}" == *"ELF 64-bit LSB"* && "${desc}" == *"ARM aarch64"* ]]
}

repair_sysroot_linker() {
  local lib_ld="${SYSROOT_DIR}/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"
  local usr_ld="${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"

  # Some sysroot extraction paths can create this as an empty directory.
  if [[ -d "${lib_ld}" ]]; then
    rm -rf "${lib_ld}"
  fi

  # Ensure lib-path loader exists (symlink to usr/lib loader is fine).
  if [[ ! -e "${lib_ld}" && -f "${usr_ld}" ]]; then
    mkdir -p "$(dirname "${lib_ld}")"
    ln -s "../../usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1" "${lib_ld}"
  fi
}

resolve_ldso_source() {
  local lib_ld="${SYSROOT_DIR}/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"
  local usr_ld="${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"

  repair_sysroot_linker

  if is_aarch64_elf "${lib_ld}"; then
    echo "${lib_ld}"
    return 0
  fi
  if is_aarch64_elf "${usr_ld}"; then
    echo "${usr_ld}"
    return 0
  fi

  err "Missing valid aarch64 dynamic loader in sysroot. Expected one of: ${lib_ld} or ${usr_ld}. Re-run setup-sysroot."
}

scrub_mixed_arch_artifacts() {
  # Desktop launchers can leave macOS objects with the same paths as larch64 outputs.
  # Remove known cross-target extension intermediates so device builds always relink.
  rm -f \
    "${ROOT_DIR}/.sconsign.dblite" \
    "${ROOT_DIR}/common/libcommon.a" \
    "${ROOT_DIR}/common/params.o" \
    "${ROOT_DIR}/common/params_pyx.cpp" \
    "${ROOT_DIR}/cereal/libcereal.a" \
    "${ROOT_DIR}/cereal/libsocketmaster.a" \
    "${ROOT_DIR}/cereal/gen/cpp/"*.capnp.c++ \
    "${ROOT_DIR}/cereal/gen/cpp/"*.capnp.h \
    "${ROOT_DIR}/cereal/gen/cpp/"*.capnp.o \
    "${ROOT_DIR}/cereal/messaging/"*.o \
    "${ROOT_DIR}/cereal/messaging/bridge" \
    "${ROOT_DIR}/msgq_repo/msgq/"*.os \
    "${ROOT_DIR}/msgq_repo/msgq/"*.o \
    "${ROOT_DIR}/msgq_repo/libmsgq.a" \
    "${ROOT_DIR}/msgq_repo/libvisionipc.a" \
    "${ROOT_DIR}/msgq_repo/msgq/ipc_pyx.so" \
    "${ROOT_DIR}/msgq_repo/msgq/visionipc/"*.os \
    "${ROOT_DIR}/msgq_repo/msgq/visionipc/"*.o \
    "${ROOT_DIR}/msgq_repo/msgq/visionipc/visionipc_pyx.so" \
    "${ROOT_DIR}/msgq/ipc_pyx.so" \
    "${ROOT_DIR}/msgq/visionipc/visionipc_pyx.so" \
    "${ROOT_DIR}/common/params_pyx.o" \
    "${ROOT_DIR}/common/params_pyx.so" \
    "${ROOT_DIR}/common/transformations/transformations.o" \
    "${ROOT_DIR}/common/transformations/transformations.so" \
    "${ROOT_DIR}/selfdrive/pandad/can_list_to_can_capnp.o" \
    "${ROOT_DIR}/selfdrive/pandad/libcan_list_to_can_capnp.a" \
    "${ROOT_DIR}/selfdrive/modeld/models/commonmodel_pyx.o" \
    "${ROOT_DIR}/selfdrive/modeld/models/commonmodel_pyx.so"
}

sync_sysroot_from_device() {
  local host="${1:-}"
  local user="${2:-comma}"
  local port="${3:-22}"
  [[ -n "${host}" ]] || err "setup-sysroot requires <device-host>."

  require_cmd rsync
  mkdir -p "${SYSROOT_DIR}"
  local ssh_cmd="ssh -p ${port} -o StrictHostKeyChecking=accept-new"

  rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:/usr/local/lib/" "${SYSROOT_DIR}/usr/local/lib/"
  rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:/usr/local/include/" "${SYSROOT_DIR}/usr/local/include/"
  rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:/lib/aarch64-linux-gnu/" "${SYSROOT_DIR}/lib/aarch64-linux-gnu/"
  rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:/usr/lib/aarch64-linux-gnu/" "${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu/"
  rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:/usr/include/" "${SYSROOT_DIR}/usr/include/"

  local vendor_src=""
  for candidate in /system/vendor/lib64 /vendor/lib64; do
    if ssh -p "${port}" -o StrictHostKeyChecking=accept-new "${user}@${host}" "test -d '${candidate}'"; then
      vendor_src="${candidate}"
      break
    fi
  done

  if [[ -n "${vendor_src}" ]]; then
    rsync -a --delete -e "${ssh_cmd}" "${user}@${host}:${vendor_src}/" "${SYSROOT_DIR}/system/vendor/lib64/"
  else
    local vendor_dst="${SYSROOT_DIR}/system/vendor/lib64"
    echo "Warning: no vendor lib64 dir found on device; falling back to usr/lib/aarch64-linux-gnu"
    if [[ -L "${vendor_dst}" || -f "${vendor_dst}" ]]; then
      rm -f "${vendor_dst}"
    elif [[ -d "${vendor_dst}" ]]; then
      rm -rf "${vendor_dst}"
    fi
    mkdir -p "${SYSROOT_DIR}/system/vendor"
    ln -s ../../usr/lib/aarch64-linux-gnu "${vendor_dst}"
  fi

  sanitize_sysroot_headers

  echo "Sysroot synced to: ${SYSROOT_DIR}"
}

setup_sysroot_from_agnos() {
  local manifest="${1:-system/hardware/tici/agnos.json}"
  local engine
  engine="$(detect_engine)"
  ensure_image_exists "${engine}"
  mkdir -p "${SYSROOT_DIR}" "${ROOT_DIR}/.cache/agnos" "${HOST_CACHE_DIR}/agnos"

  "${engine}" run --rm --platform linux/arm64 \
    --user "${DOCKER_RUN_USER}" \
    -v "${HOST_ROOT_DIR}:/work" \
    -v "${HOST_SYSROOT_DIR}:/opt/tici-sysroot" \
    -v "${HOST_CACHE_DIR}:/work/.cache" \
    -w /work \
    "${IMAGE_NAME}" \
    /usr/bin/python3 tools/laptop_device_build/extract_sysroot_from_agnos.py \
      --manifest "${manifest}" \
      --output-dir /opt/tici-sysroot \
      --cache-dir /work/.cache/agnos
}

run_larch64_scons() {
  local jobs="$1"
  shift || true
  local scrub_mode="${SP_SCONS_SCRUB_MODE:-full}"
  if [[ "${1:-}" == "--no-scrub" ]]; then
    scrub_mode="none"
    shift || true
  fi
  local engine
  local started_at
  engine="$(detect_engine)"
  ensure_image_exists "${engine}"
  ensure_sysroot_layout
  if [[ "${scrub_mode}" != "none" ]]; then
    scrub_mixed_arch_artifacts
  fi
  started_at="$(date +%s)"

  echo "==> Starting larch64 scons build"
  echo "    jobs: ${jobs}"
  echo "    note: warp artifact precompile can take several minutes on first run"

  mkdir -p "${ROOT_DIR}/.cache/scons" "${HOST_CACHE_DIR}/scons" "${HOST_VENV_DIR}"

  local extra_args=""
  local jobs_prefix="-j${jobs}"
  if [[ "$#" -gt 0 ]]; then
    for arg in "$@"; do
      case "${arg}" in
        -j|--jobs|-j*|--jobs=*)
          jobs_prefix=""
          ;;
      esac
      extra_args+=" $(printf '%q' "${arg}")"
    done
  fi

  local cmd
cmd="$(cat <<EOF
set -euo pipefail
export UV_CACHE_DIR=/work/.cache/uv
export SCONS_CACHE=/work/.cache/scons
export SP_FORCE_TICI=1
export SP_FORCE_ARCH=larch64
export SP_TICI_SYSROOT=/opt/tici-sysroot
export SP_BUILD_WARP_ARTIFACTS="\${SP_BUILD_WARP_ARTIFACTS:-0}"
export SP_SKIP_DM_TINYGRAD_PKL="\${SP_SKIP_DM_TINYGRAD_PKL:-1}"
export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/aarch64-linux-gnu:/lib/aarch64-linux-gnu:/opt/tici-sysroot/usr/local/lib:/opt/tici-sysroot/usr/lib/aarch64-linux-gnu:/opt/tici-sysroot/lib/aarch64-linux-gnu:/system/vendor/lib64:\${LD_LIBRARY_PATH:-}
export TMPDIR=/tmp
export HOME=/tmp
export PARAMS_ROOT=/tmp/params
mkdir -p "\${UV_CACHE_DIR}"
mkdir -p "\${PARAMS_ROOT}"
UV_PROJECT_ENVIRONMENT=/work/.venv-linux-arm64 uv sync --frozen --all-extras
source /work/.venv-linux-arm64/bin/activate
CACHE_FLAG="--cache-disable"
if [[ "\${SP_ENABLE_SCONS_CACHE:-0}" =~ ^(1|true|yes|on)$ ]]; then
  CACHE_FLAG=""
fi
scons ${jobs_prefix} \${CACHE_FLAG}${extra_args}
EOF
)"

  "${engine}" run --rm --platform linux/arm64 \
    --user "${DOCKER_RUN_USER}" \
    -v "${HOST_ROOT_DIR}:/work" \
    -v "${HOST_VENV_DIR}:/work/.venv-linux-arm64" \
    -v "${HOST_SYSROOT_DIR}:/opt/tici-sysroot:ro" \
    -v "${HOST_SYSROOT_DIR}/system/vendor/lib64:/system/vendor/lib64:ro" \
    -v "${HOST_CACHE_DIR}:/work/.cache" \
    -v "${HOST_CACHE_DIR}/scons:/data/scons_cache" \
    -w /work \
    "${IMAGE_NAME}" bash -lc "${cmd}"

  echo "==> larch64 scons completed in $(( $(date +%s) - started_at ))s"
}

validate_larch64_artifacts() {
  local engine
  engine="$(detect_engine)"

  echo "==> Validating larch64 runtime dependencies"
  "${engine}" run --rm --platform linux/arm64 \
    --user "${DOCKER_RUN_USER}" \
    -v "${HOST_ROOT_DIR}:/work" \
    -v "${HOST_VENV_DIR}:/work/.venv-linux-arm64:ro" \
    -v "${HOST_SYSROOT_DIR}:/opt/tici-sysroot:ro" \
    -v "${HOST_SYSROOT_DIR}/system/vendor/lib64:/system/vendor/lib64:ro" \
    -w /work \
    "${IMAGE_NAME}" bash -lc '
set -euo pipefail
ffmpeg_lib_dir="/work/.venv-linux-arm64/lib/python3.12/site-packages/ffmpeg/install/lib"
target_ffmpeg_runpath="/usr/local/venv/lib/python3.12/site-packages/ffmpeg/install/lib"
runtime_library_path="${ffmpeg_lib_dir}:/work/third_party/acados/larch64/lib:/work/third_party/libyuv/larch64/lib:/work/selfdrive/controls/lib/lateral_mpc_lib/c_generated_code:/work/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code:/opt/tici-sysroot/usr/local/lib:/opt/tici-sysroot/lib/aarch64-linux-gnu:/opt/tici-sysroot/usr/lib/aarch64-linux-gnu:/system/vendor/lib64"
failures=0

while IFS= read -r -d "" artifact; do
  if ! readelf -h "${artifact}" 2>/dev/null | grep -q "Machine:.*AArch64"; then
    continue
  fi

  dynamic="$(readelf -d "${artifact}" 2>/dev/null || true)"
  if grep -Eq "(RPATH|RUNPATH).*\/work\/" <<<"${dynamic}"; then
    echo "ERROR: ${artifact} embeds a build-host runtime path" >&2
    failures=1
  fi

  has_ffmpeg=0
  while IFS= read -r needed; do
    case "${needed}" in
      libavformat.so.*|libavcodec.so.*|libswresample.so.*|libavutil.so.*)
        has_ffmpeg=1
        if [[ ! -e "${ffmpeg_lib_dir}/${needed}" ]]; then
          echo "ERROR: ${artifact} links ${needed}, which is not shipped by the managed FFmpeg package" >&2
          failures=1
        fi
        ;;
    esac
  done < <(sed -n "s/.*Shared library: \[\([^]]*\)\].*/\1/p" <<<"${dynamic}")

  if [[ "${has_ffmpeg}" -eq 1 ]] && ! grep -Fq "${target_ffmpeg_runpath}" <<<"${dynamic}"; then
    echo "ERROR: ${artifact} links FFmpeg without the target managed-venv RUNPATH" >&2
    failures=1
  fi

  missing="$(LD_LIBRARY_PATH="${runtime_library_path}" ldd "${artifact}" 2>&1 | grep "not found" || true)"
  if [[ -n "${missing}" ]]; then
    echo "ERROR: ${artifact} has unresolved target dependencies:" >&2
    echo "${missing}" >&2
    failures=1
  fi
done < <(git ls-files -z)

exit "${failures}"
'
}

setup_host_venv() {
  if [[ ! -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    if [[ -x "${ROOT_DIR}/tools/install_python_dependencies.sh" ]]; then
      (cd "${ROOT_DIR}" && tools/install_python_dependencies.sh)
    else
      err "Missing host .venv and installer script."
    fi
  fi
}

setup_all() {
  local host="${1:-}"
  local user="${2:-comma}"
  local port="${3:-22}"

  setup_host_venv
  build_container_image

  if [[ -n "${host}" ]]; then
    sync_sysroot_from_device "${host}" "${user}" "${port}"
  else
    setup_sysroot_from_agnos "system/hardware/tici/agnos.json"
  fi
}

run_larch64_build() {
  local jobs="${1:-$(default_jobs)}"
  shift || true
  echo "==> Build pass 1/2: full project build"
  run_larch64_scons "${jobs}" "$@"
  # Ensure prebuilt runtime compatibility probes can import these modules.
  # scrub_mixed_arch_artifacts clears them at the start of each run, so
  # targeted builds must always regenerate this core set.
  # Do NOT regenerate dmonitoring_model_tinygrad.pkl on laptop builds:
  # it is backend-captured and should come from device/QCOM-compatible artifacts.
  echo "==> Build pass 2/2: required runtime artifacts"
  run_larch64_scons "${jobs}" \
    rednose/helpers/ekf_sym_pyx.so \
    common/params_pyx.so \
    common/transformations/transformations.so \
    selfdrive/pandad/pandad_api_impl.so \
    selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so \
    selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/libacados_ocp_solver_lat.so \
    selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so \
    selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/libacados_ocp_solver_long.so \
    selfdrive/modeld/models/commonmodel_pyx.so \
    cereal/messaging/bridge \
    msgq_repo/msgq/ipc_pyx.so \
    msgq_repo/msgq/visionipc/visionipc_pyx.so
  validate_larch64_artifacts
  touch "${ROOT_DIR}/prebuilt"
}

manager_artifacts_ready() {
  [[ -f "${ROOT_DIR}/msgq/ipc_pyx.so" ]] &&
  [[ -f "${ROOT_DIR}/msgq/visionipc/visionipc_pyx.so" ]] &&
  [[ -f "${ROOT_DIR}/common/params_pyx.so" ]] &&
  [[ -f "${ROOT_DIR}/selfdrive/pandad/pandad_api_impl.so" ]] &&
  [[ -f "${ROOT_DIR}/selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so" ]] &&
  [[ -f "${ROOT_DIR}/selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/libacados_ocp_solver_lat.so" ]] &&
  [[ -f "${ROOT_DIR}/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so" ]] &&
  [[ -f "${ROOT_DIR}/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/libacados_ocp_solver_long.so" ]]
}

run_manager() {
  local jobs="$(default_jobs)"
  local auto_build=1
  local manager_args=()

  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  while [[ $# -gt 0 ]]; do
    case "${1}" in
      --no-build)
        auto_build=0
        shift
        ;;
      --)
        shift || true
        manager_args=("$@")
        break
        ;;
      *)
        manager_args+=("$1")
        shift
        ;;
    esac
  done

  if [[ "${auto_build}" -eq 1 ]] && ! manager_artifacts_ready; then
    echo "Missing manager runtime artifacts. Running device-target build first..."
    run_larch64_build "${jobs}"
  fi

  local engine
  engine="$(detect_engine)"
  ensure_image_exists "${engine}"
  assert_runtime_machine "${engine}"
  ensure_sysroot_layout
  mkdir -p "${ROOT_DIR}/.cache/scons" "${HOST_CACHE_DIR}/scons" "${HOST_VENV_DIR}"

  local manager_args_q=""
  if [[ "${#manager_args[@]}" -gt 0 ]]; then
    for arg in "${manager_args[@]}"; do
      manager_args_q+=" $(printf '%q' "${arg}")"
    done
  fi

  local cmd
cmd="$(cat <<EOF
set -euo pipefail
export UV_CACHE_DIR=/work/.cache/uv
export SP_FORCE_TICI=1
export SP_FORCE_ARCH=larch64
export SP_TICI_SYSROOT=/opt/tici-sysroot
export SP_BUILD_WARP_ARTIFACTS="\${SP_BUILD_WARP_ARTIFACTS:-0}"
export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/aarch64-linux-gnu:/lib/aarch64-linux-gnu:/opt/tici-sysroot/usr/local/lib:/opt/tici-sysroot/usr/lib/aarch64-linux-gnu:/opt/tici-sysroot/lib/aarch64-linux-gnu:/system/vendor/lib64:\${LD_LIBRARY_PATH:-}
export TMPDIR=/tmp
export HOME=/tmp
export PARAMS_ROOT=/tmp/params
mkdir -p "\${UV_CACHE_DIR}"
mkdir -p "\${PARAMS_ROOT}"
UV_PROJECT_ENVIRONMENT=/work/.venv-linux-arm64 uv sync --frozen --all-extras
source /work/.venv-linux-arm64/bin/activate
cd /work
python3 system/manager/manager.py${manager_args_q}
EOF
)"

  "${engine}" run --rm --platform linux/arm64 \
    --user "${DOCKER_RUN_USER}" \
    -v "${HOST_ROOT_DIR}:/work" \
    -v "${HOST_VENV_DIR}:/work/.venv-linux-arm64" \
    -v "${HOST_SYSROOT_DIR}:/opt/tici-sysroot:ro" \
    -v "${HOST_SYSROOT_DIR}/system/vendor/lib64:/system/vendor/lib64:ro" \
    -v "${HOST_CACHE_DIR}:/work/.cache" \
    -v "${HOST_CACHE_DIR}/scons:/data/scons_cache" \
    -w /work \
    "${IMAGE_NAME}" bash -lc "${cmd}"
}

run_shell() {
  local engine
  engine="$(detect_engine)"
  ensure_image_exists "${engine}"
  ensure_sysroot_layout
  "${engine}" run --rm -it --platform linux/arm64 \
    --user "${DOCKER_RUN_USER}" \
    -v "${HOST_ROOT_DIR}:/work" \
    -v "${HOST_VENV_DIR}:/work/.venv-linux-arm64" \
    -v "${HOST_SYSROOT_DIR}:/opt/tici-sysroot:ro" \
    -v "${HOST_SYSROOT_DIR}/system/vendor/lib64:/system/vendor/lib64:ro" \
    -v "${HOST_CACHE_DIR}:/work/.cache" \
    -v "${HOST_CACHE_DIR}/scons:/data/scons_cache" \
    -w /work \
    "${IMAGE_NAME}" bash
}

doctor() {
  local failed=0

  if command -v docker >/dev/null 2>&1; then
    echo "OK: docker found"
  elif command -v podman >/dev/null 2>&1; then
    echo "OK: podman found"
  else
    echo "FAIL: install docker or podman"
    failed=1
  fi

  if command -v rsync >/dev/null 2>&1; then
    echo "OK: rsync found"
  else
    echo "WARN: rsync missing (needed only for setup-sysroot from a physical device)"
  fi

  if [[ -d "${SYSROOT_DIR}" ]]; then
    if [[ -d "${SYSROOT_DIR}/usr/local/lib" && -d "${SYSROOT_DIR}/usr/local/include" && -d "${SYSROOT_DIR}/lib/aarch64-linux-gnu" && -d "${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu" && -d "${SYSROOT_DIR}/usr/include" && -d "${SYSROOT_DIR}/system/vendor/lib64" ]]; then
      echo "OK: sysroot present at ${SYSROOT_DIR}"
    else
      echo "WARN: sysroot dir exists but is incomplete (${SYSROOT_DIR})"
      failed=1
    fi
  else
    echo "WARN: sysroot missing (${SYSROOT_DIR})"
    failed=1
  fi

  if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    echo "OK: host .venv present"
  else
    echo "WARN: host .venv missing (run scripts/laptop_device_build.sh setup)"
    failed=1
  fi

  if [[ "${failed}" -ne 0 ]]; then
    exit 1
  fi
}

main() {
  local mode="${1:-}"
  case "${mode}" in
    doctor)
      doctor
      ;;
    setup)
      shift || true
      setup_all "${1:-}" "${2:-comma}" "${3:-22}"
      ;;
    setup-sysroot)
      shift
      sync_sysroot_from_device "${1:-}" "${2:-comma}" "${3:-22}"
      ;;
    setup-sysroot-agnos)
      shift || true
      setup_sysroot_from_agnos "${1:-system/hardware/tici/agnos.json}"
      ;;
    build-image)
      build_container_image
      ;;
    build)
      shift || true
      local jobs_arg="${1:-$(default_jobs)}"
      if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
        shift || true
      else
        jobs_arg="$(default_jobs)"
      fi
      run_larch64_build "${jobs_arg}" "$@"
      ;;
    scons)
      shift || true
      run_larch64_scons "$(default_jobs)" "$@"
      ;;
    manager)
      shift || true
      run_manager "$@"
      ;;
    shell)
      run_shell
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
