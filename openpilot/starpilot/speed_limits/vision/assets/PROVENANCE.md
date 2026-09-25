These two ONNX files are copied byte-for-byte from the frozen StarPilot
`678af783` baseline under `starpilot/assets/vision_models/`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `speed_limit_us_detector.onnx` | 9,605,948 | `82408b68c79c269296f0af942130c5383cace4ee06c78e2a4690e8488720116a` |
| `speed_limit_us_value_classifier.onnx` | 6,229,930 | `07c6696e530eb940d2757d5849b4bc0f1d785cda704e5296e18c0a94959f30a5` |

The frozen tree does not identify the training set, original model publisher, or
an asset-specific redistribution license. These facts remain unresolved before
production/device distribution. The current service is development opt-in.

On the local OpenCV 4.13 host, the detector accepts a 256×256 tensor and emits
`(1, 5, 1344)`; the classifier accepts 128×128 and emits `(1, 19)`. Device
inference compatibility has not been established.
