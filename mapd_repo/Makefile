GO ?= go
BUILD_OUTPUT ?= build/mapd
export GOTOOLCHAIN := local
CAPNPC_GO_VERSION := v3.1.0-alpha.2
GO_CAPNP_PATH ?= $(shell $(GO) env GOMODCACHE)/capnproto.org/go/capnp/v3@$(CAPNPC_GO_VERSION)/std

.PHONY: build build-static capnp go-deps capnp-deps

# Build checked-in generated bindings. Dependency updates and schema generation
# are explicit operations; a normal build must not rewrite either source input.
build:
	$(GO) build -mod=readonly -trimpath -o "$(BUILD_OUTPUT)"

# Linux-only packaging build. CI records its own source stamps and evidence;
# this convenience target does not qualify a binary for a device.
build-static:
	@test "$$($(GO) env GOOS)" = linux || (echo "build-static requires Linux" >&2; exit 1)
	$(GO) build -mod=readonly -trimpath -tags "netgo osusergo" -ldflags="-extldflags=-static -s -w" -o "$(BUILD_OUTPUT)"

docker:
	docker buildx build --platform linux/arm64 --load . -t pfeiferj/mapd:latest

dockerx86:
	docker buildx build --platform linux/amd64 --load . -t pfeiferj/mapd:latest

release: docker
	docker run --pull=never --platform linux/arm64 -v ./build:/build pfeiferj/mapd:latest cp mapd /build/mapd


format:
	gofumpt -l -w .

deps: go-deps capnp-deps format-deps docker-deps

docker-deps:
	./scripts/install-docker.sh

docker-qemu-static:
	./scripts/docker-qemu-static.sh

go-deps: go.mod
	$(GO) mod download

capnp-deps:
	$(GO) install capnproto.org/go/capnp/v3/capnpc-go@$(CAPNPC_GO_VERSION)
	$(GO) mod download capnproto.org/go/capnp/v3@$(CAPNPC_GO_VERSION)

format-deps:
	go install mvdan.cc/gofumpt@latest


capnp: cereal/car/car.capnp.go cereal/custom/custom.capnp.go cereal/deprecated/deprecated.capnp.go cereal/log/log.capnp.go cereal/offline/offline.capnp.go

cereal/car/car.capnp.go: cereal/car/car.capnp
	capnp compile -I $(GO_CAPNP_PATH) -ogo cereal/car/car.capnp

cereal/custom/custom.capnp.go: cereal/custom/custom.capnp
	capnp compile -I $(GO_CAPNP_PATH) -ogo cereal/custom/custom.capnp

cereal/deprecated/deprecated.capnp.go: cereal/deprecated/deprecated.capnp
	capnp compile -I $(GO_CAPNP_PATH) -ogo cereal/deprecated/deprecated.capnp

cereal/log/log.capnp.go: cereal/log/log.capnp
	capnp compile -I $(GO_CAPNP_PATH) -ogo cereal/log/log.capnp

cereal/offline/offline.capnp.go: cereal/offline/offline.capnp
	capnp compile -I $(GO_CAPNP_PATH) -ogo cereal/offline/offline.capnp
