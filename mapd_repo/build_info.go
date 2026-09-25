package main

import "log/slog"

// Set by the repository's recorded build command, independently of Go's
// automatic VCS detection for a nested source module.
var sourceRevision = "unrecorded"
var upstreamRevision = "unrecorded"
var sourceDigest = "unrecorded"

func logBuildInfo() {
	slog.Info("map provider build", "source_revision", sourceRevision,
		"upstream_revision", upstreamRevision, "source_digest", sourceDigest)
}
