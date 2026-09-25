FROM golang:1.25.1-bookworm AS go-toolchain
FROM ubuntu:24.04
WORKDIR /usr/local/app
COPY --from=go-toolchain /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
ENV GOTOOLCHAIN=local

# Install the application dependencies
COPY scripts/install-ubuntu-deps.sh ./
RUN ./install-ubuntu-deps.sh

COPY go.mod ./
COPY go.sum ./
RUN go mod download

COPY Makefile ./
RUN make capnp-deps

COPY . /usr/local/app

RUN make build-static

RUN mv build/mapd ./mapd
RUN mv scripts/* ./

CMD ["./docker_entry.sh"]
