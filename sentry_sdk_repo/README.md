# Sentry Python SDK 2.38.0

This complete, unmodified pure-Python package is shipped as ordinary tracked
source for prebuilt AGNOS devices, which do not run dependency installation.
The SDK uses the existing requests dependencies certifi and urllib3. PC setup
also pins the same SDK in pyproject.toml and uv.lock.

The MIT license is retained in LICENSE. source-manifest.json binds each
package file, verified against the original 2.38.0 wheel distribution RECORD,
and identifies the authoritative wheel and upstream source. Optional
integrations remain intact; runtime enables only ThreadingIntegration.
