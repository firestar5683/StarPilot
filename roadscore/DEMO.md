# RoadScore demo

RoadScore makes an adaptive soundtrack from road context. The native demo shows a recorded drive in the normal comma UI while ACE-Step generates new musical passages on Chestnut. Prism is the prepared musical profile. RoadScore supplies the native port, musical continuation, buffering, quality checks, immediate gestures and synchronization; ACE-Step is a pretrained model, not a model trained by this project.

The conductor receives only road messages already delivered by replay. It requests future passages and uses immediate, source-derived gestures for short road events. Generation takes time: the buffer lets the current score continue while the next passage is being made. A curve gesture does not imply a complete new neural composition in that instant.

## Reading the overlay

The lower-left panel is 94–112 logical pixels tall on the comma four's 536 × 240 canvas, with width limited to 55% of the screen. The existing camera, lane and path display stays in place. Its rows show RoadScore's activity, profile, section, compute backend and buffered music.

| Display | Meaning |
| --- | --- |
| Prism / Aurora | Reported prepared musical profile. Prism is the primary candidate. |
| INTENT: VERSE > PRECHORUS | Current section conditioning and the next scheduled section, when provided by the runtime. These are musical intentions, not verified structural labels. |
| ACE · CHESTNUT | Reported composer and compute backend. This is not an independent GPU health probe. |
| PREPARING | The status does not yet report playback readiness. Cold preparation is separate from warm generation time. |
| READY | The runtime reports ready and no degraded condition is present. This does not certify listening quality or live-driving readiness. |
| GENERATING | A fresh passage is in flight. The elapsed time is job time, not an estimated countdown. Buffered music may continue playing. |
| DEGRADED | The runtime reports a failure, quality issue or accepted-music hold. This label takes priority even if a generation job is still in flight. |
| Holding accepted music | Previously accepted music is being reused. It is not fresh generation. |
| BUFFER 64s | Reported queued playback time. It can include accepted-music holds; it is not a fresh-music counter. `--` means unavailable. |
| STORED SCORE · NO COMPUTE | Archived score playback. It must not be presented as fresh Chestnut generation. |

Native text uses ASCII labels and measured truncation to avoid unsupported glyphs or text spilling outside the panel. The middle dot in the backend label is drawn geometrically. Long section labels end with `...`; full source values remain in the existing status/audit JSON.

## Presenter explanation

“Prism is the musical identity. The recorded road messages guide the score as they arrive. ACE generates future passages locally on Chestnut, while the buffer keeps playback moving. Short gestures can react sooner than a new generated passage. READY means the runtime is ready; GENERATING means a new passage is being made. If generation cannot keep up or a quality check fails, DEGRADED makes that visible, and the system can reuse accepted music.”

Use [EVENT.md](EVENT.md) for measured event claims. The recorded 45 W native pass was muted and does not establish physical audio, Bluetooth, live driving or modeld coexistence. Historical performance reports describe a different bench. Operational commands belong in [README.md](README.md#run-on-the-event-comma) and are for the agent/operator who owns the hardware.

## Offline UI review

From the repository root, with a Python environment containing Pillow:

```sh
python3 -m unittest discover -s roadscore/tests -v
python3 roadscore/tools/preview_overlay.py --output roadscore/results/ui-polish/overlay-states.png
```

The preview renders six full 536 × 240 synthetic canvases with the repository's Inter bitmap font atlas: preparation, ready, generating, accepted-music hold, failed composer and stored score. It uses CPU image drawing and does not open a window, contact a device, start a worker, run replay or open an audio stream. It is a layout review, not a native-rendering or hardware-validation claim. The output stays in ignored `results/`.

Generation timing and road gestures have separate space in the footer, so an active job cannot hide the event. The startup label uses the selected Prism/Aurora profile; stored playback is labeled as such from preparation onward.

The active native overlay is `prototype/overlay.py`; the pure presentation helper is `prototype/overlay_view.py`. `prototype/index.html` and `prototype/native_display.py` are older excerpt-specific bench interfaces, not the normal onroad demo. The historical style selector is not an ACE profile selector. Keep those older entrypoints distinct when presenting the current demo.
