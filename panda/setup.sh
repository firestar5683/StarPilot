#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
cd $DIR

PLATFORM=$(uname -s)

echo "installing dependencies"
if [[ $PLATFORM == "Darwin" ]]; then
  export HOMEBREW_NO_AUTO_UPDATE=1
  if ! command -v arm-none-eabi-gcc >/dev/null 2>&1; then
    brew install --cask gcc-arm-embedded
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    brew install python3
  fi
  if ! command -v gcc-13 >/dev/null 2>&1; then
    brew install gcc@13
  fi
elif [[ $PLATFORM == "Linux" ]]; then
  # for AGNOS since we clear the apt lists
  if [[ ! -d /"var/lib/apt/" ]]; then
    sudo apt update
  fi

  sudo apt-get install -y --no-install-recommends \
    curl ca-certificates \
    make g++ git libnewlib-arm-none-eabi \
    libusb-1.0-0 \
    gcc-arm-none-eabi \
    python3-dev python3-pip python3-venv
else
  echo "WARNING: unsupported platform. skipping apt/brew install."
fi

if ! command -v uv &>/dev/null; then
  echo "'uv' is not installed. Installing 'uv'..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # doesn't require sourcing on all platforms
  set +e
  source $HOME/.local/bin/env
  set -e
fi

export UV_PROJECT_ENVIRONMENT="$DIR/.venv"
uv sync --all-extras --frozen
source "$DIR/.venv/bin/activate"
