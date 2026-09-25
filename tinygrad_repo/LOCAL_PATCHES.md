# Local compatibility patch

`tinygrad/helpers.py::fetch_fw` reads installed `.zst` firmware through the
`zstandard` streaming decoder on Python before 3.14. AGNOS 19.6.20's
`amdgpu/psp_14_0_2_sos.bin.zst` has no frame content-size field, so the former
one-shot decoder raised before Tinygrad could compare the decompressed bytes
with its pinned firmware SHA-256. Streaming retains the same hash check and
the pinned upstream fallback for a missing or mismatched local file. It does
not change device firmware or the AMD runtime protocol.
