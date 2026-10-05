<p align="center">
  <img src="macos/Resources/Assets.xcassets/AppIcon.appiconset/icon_128x128@2x.png" width="128" height="128" alt="Jetlink icon">
</p>

<h1 align="center">Jetlink</h1>

<p align="center">
  Run openpilot's large driving models on a computer connected to your comma.
</p>

**Jetlink is experimental.** It requires zoompilot's
[`develop` branch](https://github.com/zoompilot/zoompilot/tree/develop).
If the link drops or lags while engaged, the comma says **TAKE CONTROL** and
stays engaged on the small model. Be ready to take over.

## Quick start

You need a **comma 3X or comma 4**, a **USB 3 data cable**, and **separate power
for the comma and computer**. Set up offroad with both devices online.

Choose your computer. Each guide covers installation and connecting the comma.

| Computer | Setup guide |
| --- | --- |
| Jetson Orin Nano Super | [Set up a Jetson](docs/jetson.md) |
| Apple silicon Mac | [Set up a Mac](docs/macos-app.md) |
| Linux PC with an NVIDIA GPU | [Set up a Linux PC](docs/linux-pc.md) |
| iPhone or iPad with USB-C | [Install with TestFlight](docs/iphone-app.md) |
| Android phone with USB 3 | [Try the experimental Android app](docs/android-app.md) |

## Demos

### Jetson

<a href="docs/images/install-demo.mp4"><img src="docs/images/install-demo.webp" width="100%" alt="Jetlink installer on a Jetson"></a>

<details>
<summary>Watch the web page</summary>

<a href="docs/images/webui-demo.mp4"><img src="docs/images/webui-demo.webp" width="100%" alt="The Jetson's web page on a phone and a computer, with simulated drive data: sign in, frame timing against the 50 ms budget, a model downloaded and prepared (sped up), the power setting applied, and keep awake"></a>

</details>

### Mac

<a href="docs/images/mac-demo.mp4"><img src="docs/images/mac-demo.webp" width="100%" alt="Jetlink for Mac: Use Model downloads and prepares a model, the comma connects over USB, and Status shows each frame against the 50 ms budget"></a>

### iPhone and iPad (experimental)

Simulator demo.

<a href="docs/images/iphone-demo.mp4"><img src="docs/images/iphone-demo.webp" width="100%" alt="Jetlink for iPhone, recorded in the iOS Simulator: Get downloads and prepares a model, the comma connects over USB, and Status shows each frame against the 50 ms budget, with timings modeled on an iPhone 17 Pro measurement"></a>

<a href="https://testflight.apple.com/join/DAsYk5sP"><img src="docs/images/testflight-badge.svg" alt="Available on TestFlight" height="40"></a>

### Android (experimental)

Emulator demo.

<a href="docs/images/android-demo.mp4"><img src="docs/images/android-demo.webp" width="100%" alt="Jetlink for Android, recorded in the Android emulator: Get downloads a model, the comma connects over USB, and Status shows each frame against the 50 ms budget. The download is sped up, the emulator's CPU preparation cut, and the model's time modeled on an estimate for a Snapdragon 8 Gen 3"></a>

<a id="comma-setup-all-platforms"></a>
<a id="jetson-or-linux-pc"></a>
<a id="linux-pc"></a>
<a id="what-to-expect-when-driving"></a>
<a id="if-something-is-wrong"></a>
<a id="more"></a>

## Help

[Setup guides](docs/README.md#set-up) ·
[Daily use](docs/using-jetlink.md) ·
[Troubleshooting](docs/troubleshooting.md) ·
[Operating limits](docs/status.md)

## License

[MIT](LICENSE).
