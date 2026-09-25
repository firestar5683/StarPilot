ARG BASE_IMAGE=ghcr.io/commaai/openpilot-base-aarch64@sha256:c4f206250ec2cbee493589b836e517a3de91281d8d9e4b01f370b5b600a0d143
FROM ${BASE_IMAGE}

ARG CAPNP_VERSION=1.0.1
ARG CAPNP_SHA256=5bdb16f6b389a9e29b04214b9bae1759e8b7fe2b45049d7e3f1f286ba050a200

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
WORKDIR /work

# Keep this image minimal; dependency resolution is done by uv inside the workspace.
# rsync/ssh-client are needed for optional sysroot sync from a comma device.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    rsync \
    openssh-client \
    e2fsprogs \
    android-sdk-libsparse-utils \
    qemu-user-static \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    gcc-arm-none-eabi \
    binutils-arm-none-eabi \
    cmake \
    python3-pip \
    xz-utils \
    git \
  && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    tmpdir="$(mktemp -d)"; \
    curl -fsSL "https://github.com/capnproto/capnproto/archive/refs/tags/v${CAPNP_VERSION}.tar.gz" -o "${tmpdir}/capnproto.tar.gz"; \
    printf '%s  %s\n' "${CAPNP_SHA256}" "${tmpdir}/capnproto.tar.gz" | sha256sum -c -; \
    tar -xzf "${tmpdir}/capnproto.tar.gz" -C "${tmpdir}"; \
    cmake -S "${tmpdir}/capnproto-${CAPNP_VERSION}/c++" -B "${tmpdir}/build" \
      -DBUILD_TESTING=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local; \
    cmake --build "${tmpdir}/build" -j"$(nproc)"; \
    cmake --install "${tmpdir}/build"; \
    ldconfig; \
    capnp --version; \
    rm -rf "${tmpdir}"

RUN /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages uv==0.12.5

# Fix for "dubious ownership" git errors when mounting folders on Linux hosts.
RUN git config --global --add safe.directory /work
