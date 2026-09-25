#!/bin/sh
set -eu

apt update
apt install -y \
  build-essential \
  pkg-config \
  wget \
  capnproto \
  zlib1g-dev \
  git \
  rclone \
  osmium-tool
