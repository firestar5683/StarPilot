# Verified stock QCOM artifacts for laptop builds

The ARM64 laptop container cannot compile QCOM models without `/dev/kgsl-3d0`. Full `./build` imports six stock model/warp artifacts only when `.cache/qcom-artifact-package` contains `manifest.json` and `artifacts/<name>` for every stock target. The package is local and Git ignored. Device builds keep the native compiler commands.

Generate the manifest on the source device or a trusted matching source tree, using its already compiled stock artifact directory:

```sh
python3 tools/laptop_device_build/qcom_artifact_contract.py record "$SOURCE_ROOT" "$SOURCE_ROOT/openpilot/selfdrive/modeld/models" > manifest.json
```

Copy the six manifest-listed artifacts into `.cache/qcom-artifact-package/artifacts/` and the manifest into `.cache/qcom-artifact-package/manifest.json`. The import checks both ONNX files, selected tinygrad compiler sources, camera/model geometry, native QCOM command recipes, every artifact's size and SHA-256, and the QCOM pickle backend before copying. A changed input or incomplete package fails the build. The manifest records provenance; it is not a cryptographic attestation of who produced the artifacts. A relocated device source can generate the same normalized recipe signature when its actual inputs match.

## Reusing artifacts after a runtime change

A reviewed change limited to `tinygrad_repo/tinygrad/runtime/ops_qcom.py` can reuse the original artifacts after paired QCOM runs compare the old and new runtime. Preserve `manifest.json`: running `record` again would incorrectly attribute the existing binaries to new build inputs. Put the compatibility record in `compatibility.json` and its supporting files in `compatibility/` instead. Other source or compiler-command changes still require a new build package.

The version-1 compatibility record contains:

- `method`: `paired-qcom-output-sha256`.
- `build_manifest_sha256` and `compatible_source_sha256`: the original manifest's byte hash and the new checkout's `source-signature`.
- `changed_source`: `path`, `build_sha256`, and `runtime_sha256` for the changed runtime file.
- `artifact_sha256`: every original manifest target and its unchanged artifact hash.
- `paired_outputs`: every stock target's three observations in A/B/A input order. Each observation records `input`, `shape`, `dtype`, `build_sha256`, and `runtime_sha256`; each old/new output pair must match.
- `evidence_files`: one to eight filenames mapped to SHA-256 hashes. Files must be regular, nonempty, at most 128 KiB each, and directly inside `compatibility/`.

Keep the input construction, recurrent-state handling, runtime identities and run results in the evidence files so another developer can review the comparison. This contract validates the recorded bindings and sampled equivalence; it does not independently attest who ran the hardware or establish equivalence for every input. The regular import checks still validate all six artifacts, even when only one is requested.
