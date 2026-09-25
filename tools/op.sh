#!/usr/bin/env bash

if [[ ! "${BASH_SOURCE[0]}" = "${0}" ]]; then
  echo "Invalid invocation! This script must not be sourced."
  echo "Run 'op.sh' directly or check your .bashrc for a valid alias"
  return 0
fi

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
UNDERLINE='\033[4m'
BOLD='\033[1m'
NC='\033[0m'

SHELL_NAME="$(basename "${SHELL}")"
RC_FILE="${HOME}/.$(basename "${SHELL}")rc"
if [ "$(uname)" == "Darwin" ] && [ "$SHELL" == "/bin/bash" ]; then
  RC_FILE="$HOME/.bash_profile"
fi

function retry() {
  local attempts=$1
  shift
  for i in $(seq 1 "$attempts"); do
    if "$@"; then
      return 0
    fi
    if [ "$i" -lt "$attempts" ]; then
      echo "  Attempt $i/$attempts failed, retrying in 5s..."
      sleep 5
    fi
  done
  return 1
}

function op_run_command() {
  CMD="$*"

  echo -e "${BOLD}Running command →${NC} $CMD │"
  for ((i=0; i<$((19 + ${#CMD})); i++)); do
    echo -n "─"
  done
  echo -e "┘\n"

  if [[ -z "$DRY" ]]; then
    "$@"
  fi
}

# be default, assume openpilot dir is in current directory
OPENPILOT_ROOT=$(pwd)
function op_get_openpilot_dir() {
  # First try traversing up the directory tree
  while [[ "$OPENPILOT_ROOT" != '/' ]];
  do
    if find "$OPENPILOT_ROOT/launch_openpilot.sh" -maxdepth 1 -mindepth 1 &> /dev/null; then
      return 0
    fi
    OPENPILOT_ROOT="$(readlink -f "$OPENPILOT_ROOT/"..)"
  done

  # Fallback to hardcoded directories if not found
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
  for dir in "$(readlink -f "$SCRIPT_DIR/../..")" "$HOME/openpilot" "/data/openpilot"; do
    if [[ -f "$dir/launch_openpilot.sh" ]]; then
      OPENPILOT_ROOT="$dir"
      return 0
    fi
  done
}

function op_install_post_commit() {
  op_get_openpilot_dir
  op_check_openpilot_dir
  local git_dir common_dir hooks_dir hook_source
  git_dir="$(git -C "$OPENPILOT_ROOT" rev-parse --absolute-git-dir)"
  common_dir="$(git -C "$OPENPILOT_ROOT" rev-parse --path-format=absolute --git-common-dir)"
  if [[ "$git_dir" != "$common_dir" || -d "$common_dir/worktrees" ]]; then
    echo "Hook installation requires a standalone checkout without linked worktrees; shared hooks were not changed."
    return 1
  fi
  hooks_dir="$(git -C "$OPENPILOT_ROOT" rev-parse --path-format=absolute --git-path hooks)"
  if [[ "$hooks_dir" != "$git_dir/hooks" ]]; then
    echo "A custom hooks directory is configured; install the linter there manually. Existing hooks were not changed."
    return 1
  fi
  hook_source="$(cd "$OPENPILOT_ROOT" && pwd)/scripts/post-commit"
  mkdir -p "$hooks_dir/post-commit.d"
  if [[ ( -e "$hooks_dir/post-commit" || -L "$hooks_dir/post-commit" ) && ! "$hooks_dir/post-commit" -ef "$hook_source" ]]; then
    if [[ -e "$hooks_dir/post-commit.d/post-commit" || -L "$hooks_dir/post-commit.d/post-commit" ]]; then
      echo "An earlier post-commit hook is already saved; resolve the two existing hooks before installing."
      return 1
    fi
    mv "$hooks_dir/post-commit" "$hooks_dir/post-commit.d/post-commit"
  fi
  ln -sf "$hook_source" "$hooks_dir/post-commit"
}

function op_check_openpilot_dir() {
  echo "Checking for openpilot directory..."
  if [[ -f "$OPENPILOT_ROOT/launch_openpilot.sh" ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] openpilot found."
    return 0
  fi
  echo -e " ↳ [${RED}✗${NC}] openpilot directory not found! Make sure that you are"
  echo "       inside the openpilot directory or specify one with the"
  echo "       --dir option!"
  return 1
}

function op_check_git() {
  echo "Checking for git..."
  if ! command -v "git" > /dev/null 2>&1; then
    echo -e " ↳ [${RED}✗${NC}] git not found on your system!"
    return 1
  else
    echo -e " ↳ [${GREEN}✔${NC}] git found."
  fi

  echo "Checking ordinary checkout resources..."
  python3 "$OPENPILOT_ROOT/tools/resources/check.py" || return 1

  echo "Checking tracked dependency sources..."
  op_check_dependencies
}

function op_check_dependencies() {
  local python_bin="$OPENPILOT_ROOT/.venv/bin/python3"
  if [[ ! -x "$python_bin" ]]; then
    python_bin=python3
  fi
  "$python_bin" "$OPENPILOT_ROOT/tools/vendor/check.py" "$@"
}

function op_check_os() {
  echo "Checking for compatible os version..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] Linux detected."
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] macOS detected."
  else
    echo -e " ↳ [${RED}✗${NC}] OS type $OSTYPE not supported!"
    return 1
  fi
}

function op_check_venv() {
  echo "Checking for venv..."
  if [[ -f "$OPENPILOT_ROOT/.venv/bin/activate" ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] venv detected."
  else
    echo -e " ↳ [${RED}✗${NC}] Can't activate venv in '$OPENPILOT_ROOT'. Assuming global env!"
  fi
}

function op_before_cmd() {
  if [[ ! -z "$NO_VERIFY" ]]; then
    return 0
  fi

  op_get_openpilot_dir
  cd "$OPENPILOT_ROOT"

  result="$((op_check_openpilot_dir ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_git ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_os ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_venv ) 2>&1)" || (echo -e "$result" && return 1)

  op_activate_venv

  if [[ -z $VERBOSE ]]; then
    echo -e "${BOLD}Checking system →${NC} [${GREEN}✔${NC}]"
  else
    echo -e "$result"
  fi
}

function op_setup() {
  echo "Installing op system-wide..."
  OP_SH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )/op.sh"
  CMD=$(cat <<EOF
alias op='$OP_SH "\$@"'
_op_completions() { [ "\$COMP_CWORD" -eq 1 ] && COMPREPLY=(\$(compgen -W "\$(awk '/shift 1; op_/{print \$1}' $OP_SH)" -- "\${COMP_WORDS[1]}")); }
[ -n "\$BASH_VERSION" ] && complete -F _op_completions -o default op
EOF
)
  grep -q "alias op=" "$RC_FILE" 2>/dev/null || printf '\n%s\n' "$CMD" >> "$RC_FILE"
  echo -e " ↳ [${GREEN}✔${NC}] op installed successfully. Open a new shell to use it."

  op_get_openpilot_dir
  cd "$OPENPILOT_ROOT"

  op_check_openpilot_dir
  op_check_os

  # Local Python package sources are shipped in the checkout. Bootstrap Python
  # before running the full manifest validator on machines without Python yet.
  for path in upstream-sync.json panda/pyproject.toml opendbc_repo/pyproject.toml msgq_repo/pyproject.toml rednose_repo/pyproject.toml teleoprtc_repo/pyproject.toml tinygrad_repo/pyproject.toml; do
    if [[ ! -f "$OPENPILOT_ROOT/$path" ]]; then
      echo "Missing tracked dependency source: $path. Restore the complete checkout."
      return 1
    fi
  done

  echo "Installing dependencies..."
  st="$(date +%s)"
  SETUP_SCRIPT="tools/setup_dependencies.sh"
  if ! "$OPENPILOT_ROOT/$SETUP_SCRIPT"; then
    echo -e " ↳ [${RED}✗${NC}] Dependencies installation failed!"
    return 1
  fi
  et="$(date +%s)"
  echo -e " ↳ [${GREEN}✔${NC}] Dependencies installed successfully in $((et - st)) seconds."

  op_activate_venv
  op_check_dependencies

  op_check
}

function op_auth() {
  op_before_cmd
  op_run_command openpilot/tools/lib/auth.py "$@"
}

function op_activate_venv() {
  # bash 3.2 can't handle this without the 'set +e'
  set +e
  source "$OPENPILOT_ROOT/.venv/bin/activate" &> /dev/null || true
  set -e

  # persist venv on PATH across GitHub Actions steps
  if [ -n "$GITHUB_PATH" ]; then
    echo "$OPENPILOT_ROOT/.venv/bin" >> "$GITHUB_PATH"
  fi
}

function op_venv() {
  op_before_cmd

  if [[ ! -f "$OPENPILOT_ROOT/.venv/bin/activate" ]]; then
    echo -e "No venv found in '$OPENPILOT_ROOT'"
    return 1
  fi

  case $SHELL_NAME in
    "zsh")
      ZSHRC_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'tmp_zsh')
      echo "source \"$RC_FILE\"; source \"$OPENPILOT_ROOT/.venv/bin/activate\"" >> "$ZSHRC_DIR/.zshrc"
      ZDOTDIR=$ZSHRC_DIR zsh ;;
    *)
      bash --rcfile <(echo "source \"$RC_FILE\"; source \"$OPENPILOT_ROOT/.venv/bin/activate\"") ;;
  esac
}

function op_adb() {
  op_before_cmd
  op_run_command tools/scripts/adb_ssh.sh "$@"
}

function op_ssh() {
  op_before_cmd
  op_run_command tools/scripts/ssh.py "$@"
}

function op_script() {
  op_before_cmd

  case $1 in
    som-debug )  op_run_command panda/scripts/som_debug.sh "${@:2}" ;;
    * )
      echo -e "Unknown script '$1'. Available scripts:"
      echo -e "  ${BOLD}som-debug${NC}    SOM serial debug console via panda"
      return 1
      ;;
  esac
}

function op_check() {
  VERBOSE=1
  op_before_cmd
  unset VERBOSE
}

function op_esim() {
  op_before_cmd
  op_run_command openpilot/common/esim/esim.py "$@"
}

function op_build() {
  CDIR=$(pwd)
  op_before_cmd
  cd "$CDIR"
  if [[ -f "/AGNOS" ]]; then
    # needed on AGNOS to not run out of memory
    op_run_command openpilot/system/manager/build.py
  else
    op_run_command scons -u "$@"
  fi
}

function op_juggle() {
  op_before_cmd
  op_run_command openpilot/tools/plotjuggler/juggle.py "$@"
}

function op_lint() {
  op_before_cmd
  op_run_command scripts/lint/lint.sh "$@"
}

function op_test() {
  op_before_cmd
  op_run_command python3 tools/ci/run_host_tests.py "$@"
}

function op_replay() {
  op_before_cmd
  op_run_command openpilot/tools/replay/replay "$@"
}

function op_cabana() {
  op_before_cmd
  op_run_command openpilot/tools/cabana/cabana "$@"
}

function op_sim() {
  op_before_cmd
  op_run_command exec openpilot/tools/sim/run_bridge.py &
  op_run_command exec openpilot/tools/sim/launch_openpilot.sh
}

function op_clip() {
  op_before_cmd
  op_run_command openpilot/tools/clip/run.py "$@"
}

function op_docs() {
  op_before_cmd
  op_run_command python docs/serve.py "$@"
}

function op_check_agnos_update() {
  if [[ ! -f "/AGNOS" ]]; then
    return 0
  fi

  local choice current_version target_version update_policy target_config
  current_version="$(< /VERSION)"
  target_config="$(unset AGNOS_VERSION AGNOS_UPDATE_POLICY; source "$OPENPILOT_ROOT/launch_env.sh"; printf '%s\n%s\n' "$AGNOS_VERSION" "${AGNOS_UPDATE_POLICY:-auto}")"
  target_version="${target_config%%$'\n'*}"
  update_policy="${target_config#*$'\n'}"
  if [[ -z "$target_version" || ( "$update_policy" != "auto" && "$update_policy" != "retain" ) ]]; then
    echo "Invalid AGNOS installation policy. No OS update was attempted."
    return 1
  fi

  if [[ "$current_version" == "$target_version" ]]; then
    return 0
  fi

  if [[ "$update_policy" == "retain" ]]; then
    echo "This StarPilot build retains AGNOS $target_version; installed $current_version. No OS update was attempted."
    return 1
  fi

  echo -e "${BOLD}AGNOS update available:${NC} $current_version → $target_version"
  if read -r -p "Install it now? [y/N] " choice && [[ "$choice" =~ ^[Yy]$ ]]; then
    op_run_command "$OPENPILOT_ROOT/openpilot/common/hardware/comma/agnos.py" --swap \
      "$OPENPILOT_ROOT/openpilot/common/hardware/comma/agnos.json"

    if read -r -p "Reboot now to apply the update? [y/N] " choice && [[ "$choice" =~ ^[Yy]$ ]]; then
      op_run_command sudo reboot
    else
      echo "Reboot before starting openpilot to apply the AGNOS update."
    fi
  fi
}

function op_switch() {
  op_get_openpilot_dir
  op_check_openpilot_dir
  cd "$OPENPILOT_ROOT"

  REMOTE="origin"
  if [ "$#" -gt 1 ]; then
    REMOTE="$1"
    shift
  fi

  if [ -z "$1" ]; then
    echo -e "${BOLD}${UNDERLINE}Usage:${NC} op switch [REMOTE] <BRANCH>"
    return 1
  fi
  BRANCH="$1"

  git config --replace-all "remote.${REMOTE}.fetch" "+refs/heads/*:refs/remotes/${REMOTE}/*"
  git -c submodule.recurse=false fetch --no-recurse-submodules "$REMOTE" "$BRANCH"
  local target_commit
  target_commit="$(git rev-parse 'FETCH_HEAD^{commit}')"
  # Validate the target before discarding the current checkout's changes.
  op_check_dependencies --revision "$target_commit"
  git -c submodule.recurse=false checkout --force --no-recurse-submodules -B "$BRANCH" "$target_commit"
  git branch --set-upstream-to="${REMOTE}/${BRANCH}" "$BRANCH"
  git -c submodule.recurse=false reset --hard --no-recurse-submodules "$target_commit"
  git clean -df
  op_check_dependencies

  # remove openpilot update flag if present
  rm -f .overlay_init

  op_check_agnos_update
}

function op_start() {
  if [[ -f "/AGNOS" ]]; then
    op_before_cmd
    op_check_agnos_update
    op_run_command sudo systemctl restart comma "$@"
  fi
}

function op_stop() {
  if [[ -f "/AGNOS" ]]; then
    op_before_cmd
    op_run_command sudo systemctl stop comma "$@"
  fi
}

function op_default() {
  echo "An openpilot helper"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Description:${NC}"
  echo "  op is your entry point for all things related to openpilot development."
  echo "  op is only a wrapper for existing scripts, tools, and commands."
  echo "  op will always show you what it will run on your system."
  echo ""
  echo -e "${BOLD}${UNDERLINE}Usage:${NC} op [OPTIONS] <COMMAND>"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [System]:${NC}"
  echo -e "  ${BOLD}auth${NC}         Authenticate yourself for API use"
  echo -e "  ${BOLD}check${NC}        Check the development environment (git, os) to start using openpilot"
  echo -e "  ${BOLD}esim${NC}         Manage eSIM profiles on your comma device"
  echo -e "  ${BOLD}venv${NC}         Activate the python virtual environment"
  echo -e "  ${BOLD}setup${NC}        Install the 'op' tool and openpilot dependencies"
  echo -e "  ${BOLD}build${NC}        Run the openpilot build system in the current working directory"
  echo -e "  ${BOLD}switch${NC}       Switch to a different git branch with a clean slate (nukes any changes)"
  echo -e "  ${BOLD}start${NC}        Starts (or restarts) openpilot"
  echo -e "  ${BOLD}stop${NC}         Stops openpilot"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Tooling]:${NC}"
  echo -e "  ${BOLD}juggle${NC}       Run PlotJuggler"
  echo -e "  ${BOLD}replay${NC}       Run Replay"
  echo -e "  ${BOLD}cabana${NC}       Run Cabana"
  echo -e "  ${BOLD}clip${NC}         Run clip (linux only)"
  echo -e "  ${BOLD}docs${NC}         Build or serve the openpilot documentation"
  echo -e "  ${BOLD}adb${NC}          Run adb shell"
  echo -e "  ${BOLD}ssh${NC}          comma prime SSH helper"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Scripts]:${NC}"
  echo -e "  ${BOLD}script${NC}       Run a script (e.g. op script som-debug)"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Testing]:${NC}"
  echo -e "  ${BOLD}sim${NC}          Run openpilot in a simulator"
  echo -e "  ${BOLD}lint${NC}         Run the linter"
  echo -e "  ${BOLD}post-commit${NC}  Install the linter as a post-commit hook"
  echo -e "  ${BOLD}test${NC}         Run all unit tests"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Options:${NC}"
  echo -e "  ${BOLD}-d, --dir${NC}"
  echo "          Specify the openpilot directory you want to use"
  echo -e "  ${BOLD}--dry${NC}"
  echo "          Don't actually run anything, just print what would be run"
  echo -e "  ${BOLD}-n, --no-verify${NC}"
  echo "          Skip environment check before running commands"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Examples:${NC}"
  echo "  op setup"
  echo "          Run the setup script to install"
  echo "          openpilot's dependencies."
  echo ""
  echo "  op build -j4"
  echo "          Compile openpilot using 4 cores"
  echo ""
  echo "  op juggle --demo"
  echo "          Run PlotJuggler on the demo route"
}


function _op() {
  # parse Options
  case $1 in
    -d | --dir )       shift 1; OPENPILOT_ROOT="$1"; shift 1 ;;
    --dry )            shift 1; DRY="1" ;;
    -n | --no-verify ) shift 1; NO_VERIFY="1" ;;
  esac

  # parse Commands
  case $1 in
    auth )          shift 1; op_auth "$@" ;;
    venv )          shift 1; op_venv "$@" ;;
    check )         shift 1; op_check "$@" ;;
    esim )          shift 1; op_esim "$@" ;;
    setup )         shift 1; op_setup "$@" ;;
    build )         shift 1; op_build "$@" ;;
    juggle )        shift 1; op_juggle "$@" ;;
    cabana )        shift 1; op_cabana "$@" ;;
    lint )          shift 1; op_lint "$@" ;;
    test )          shift 1; op_test "$@" ;;
    replay )        shift 1; op_replay "$@" ;;
    clip )          shift 1; op_clip "$@" ;;
    docs )          shift 1; op_docs "$@" ;;
    sim )           shift 1; op_sim "$@" ;;
    switch )        shift 1; op_switch "$@" ;;
    start )         shift 1; op_start "$@" ;;
    stop )          shift 1; op_stop "$@" ;;
    restart )       shift 1; op_restart "$@" ;;
    post-commit )   shift 1; op_install_post_commit "$@" ;;
    adb )           shift 1; op_adb "$@" ;;
    ssh )           shift 1; op_ssh "$@" ;;
    script )        shift 1; op_script "$@" ;;
    * ) op_default "$@" ;;
  esac
}

_op "$@"
