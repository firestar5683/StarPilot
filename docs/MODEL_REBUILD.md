# StarPilot Unified Model Rebuild

This workflow rebuilds StarPilot driving and driver-monitoring artifacts for the vendored tinygrad revision. Driving-model behavior versions remain manifest metadata; every runtime driving artifact uses the `tinygrad_single_v1` layout.

## Safety

- The supported build device is `comma@192.168.3.110`.
- Never run these commands against `192.168.3.109`.
- Normal artifacts target QCOM. External-GPU artifacts must be compiled explicitly and tagged in the manifest.
- Keep source ONNX files and compiled PKLs on the T5 workspace, not the comma.

## Workspace

The default workspace is:

```text
/Volumes/T5/StarPilot-Model-Rebuild-2026-06-22/
```

Important directories:

- `onnx/<model-id>/`: ID-prefixed source ONNX files.
- `compiled/`: completed unified driving PKLs.
- `driver-monitoring/`: DM ONNX, model PKL, metadata, and camera warps.
- `ready-for-resources/`: flat repository-upload handoff.
- Oversized models are represented by repository-safe `.p00`, `.p01`, and `.sha256` files in `ready-for-resources/`.
- `logs/`: one remote compilation log per model.
- `results/`: source and artifact checksum records.
- `manifests/`: generated `model_names_v22.json`.

## Initialize And Extract

```bash
python3 scripts/model_rebuild_pipeline.py init
python3 scripts/model_rebuild_pipeline.py extract \
  --base-manifest /path/to/model_names_v21.json
```

Extraction streams Git blobs directly to disk. LFS pointers are resolved from the local object cache or fetched by object ID, then checked against the pointer SHA-256 and size. Binary ONNX data is never stored in a shell variable.

To retry one source:

```bash
python3 scripts/model_rebuild_pipeline.py extract \
  --model pop22 \
  --base-manifest /path/to/model_names_v21.json
```

Source commits are defined in `scripts/model_source_map_v22.json`.

## Compile

Compile one model:

```bash
python3 scripts/model_rebuild_pipeline.py compile \
  --model pop22 \
  --base-manifest /path/to/model_names_v21.json
```

Compile or resume the full catalog:

```bash
python3 scripts/model_rebuild_pipeline.py compile \
  --base-manifest /path/to/model_names_v21.json
```

Existing artifacts are skipped unless `--force` is passed. Each model is staged in its own remote input directory, compiled on `.110`, copied back to the T5, hashed, and copied into `ready-for-resources/`. Failures are written to `results/<id>_failure.json`; rerunning the same command resumes incomplete models.

Validate one or all completed artifacts with synthetic camera inputs on QCOM:

```bash
python3 scripts/model_rebuild_pipeline.py validate \
  --model pop22 \
  --base-manifest /path/to/model_names_v21.json
```

The lower-level device compiler also supports direct use:

```bash
./models --model pop22 --input-format split --version v11
./models --model deeprl3v2 --input-format supercombo --version v15
```

For a model that cannot run on the device GPU, compile with the USB AMD GPU attached:

```bash
./models --lebowski --gpu
```

The ASM2464PD bridge must run the current tinygrad custom firmware from
https://github.com/tinygrad/asm2464pd-firmware. Its USB product string starts
with `custom`; the legacy `USB 3.2 PCIe TinyEnclosure` patch is not compatible
with comma's current external-GPU runtime. Firmware flashing is a separate,
explicit hardware setup step and StarPilot never performs it automatically.

The dynamic flag (`--lebowski` above) sets the output and manifest model ID;
when only one source model is staged, its ONNX filename does not need to match
that ID. Input format and behavior version are inferred. `--external-gpu`
remains available as a compatibility alias for `--gpu`.

This emits a streaming out-of-band pickle and keeps QCOM available for camera warps. Its manifest entry must include:

```json
{
  "id": "lebowski",
  "uses_external_gpu": true
}
```

Only tagged models activate the external GPU. If the GPU or artifact is unavailable, runtime falls back to the built-in model; all untagged models retain the existing QCOM path.

`--version` records behavioral semantics only. It does not change artifact layout.

If the compiled PKL exceeds 100 MiB, `./models` automatically keeps the full
local PKL and creates 95 MiB upload parts beside it:

```text
deeprl3v2_driving_tinygrad.pkl
deeprl3v2_driving_tinygrad.pkl.p00
deeprl3v2_driving_tinygrad.pkl.p01
deeprl3v2_driving_tinygrad.pkl.sha256
```

To split an already compiled artifact:

```bash
./models --split-artifact /path/to/deeprl3v2_driving_tinygrad.pkl \
  --output-dir /path/to/upload-ready
```

Upload only the numbered parts and checksum when the full PKL exceeds the
repository limit. The downloader reassembles into a temporary file, verifies
the companion SHA-256, and atomically installs the final PKL. No manifest field
is required for multipart artifacts.

## Driver Monitoring

Stage the current DM ONNX in `uncompiledmodels`, then run:

```bash
./models --dm \
  --input-dir /data/openpilot/uncompiledmodels \
  --output-dir /tmp/dm_artifacts
```

This builds:

- `dmonitoring_model_tinygrad.pkl`
- `dmonitoring_model_metadata.pkl`
- `dm_warp_1928x1208_tinygrad.pkl`
- `dm_warp_1344x760_tinygrad.pkl`

All four files must be updated together.

## Manifest

Generate v22 after compilation:

```bash
python3 scripts/model_rebuild_pipeline.py manifest \
  --base-manifest /path/to/model_names_v21.json
```

The generator preserves existing IDs and behavioral metadata and adds
`deeprl3v2`. Manifest v22 implies the unified single-PKL runtime layout.
Repository-hosted multipart files are discovered by naming convention, so no
size, hash, format, or part-count metadata is required.

`uses_external_gpu` is optional and defaults to `false`.

## Runtime Verification

Compilation validates JIT capture/replay, pickle round-trip, finite outputs, metadata slices, and both camera warps. Before release:

1. Select representative v8, v11, v12, v15, and supercombo models.
2. Confirm `modeld` stays running.
3. Confirm finite `modelV2` path, lane-line, lead, pose, and action data.
4. Confirm `driverStateV2` on both supported camera resolutions.
5. Test download, selection, deletion, randomization, migration, and fallback in QT, raylib/mici, and Galaxy.

The built-in South Carolina artifact is `selfdrive/modeld/models/driving_tinygrad.pkl`. If migration cannot download the selected v22 artifact, StarPilot switches to that built-in model.
