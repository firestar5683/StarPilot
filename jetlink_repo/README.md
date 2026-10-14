# Jetlink runtime for StarPilot

This subtree supplies the Jetlink remote-model client used by **StarPilot**.
For installing, connecting, selecting, and running it with StarPilot, follow
[the StarPilot JetLink guide](../openpilot/starpilot/models/JETLINK.md).

The comma runs StarPilot; the connected host runs the upstream Jetlink application.
Host apps, installers, development references, and original history are maintained
in [ZoomPilot / Jetlink](https://github.com/zoompilot/jetlink/tree/c17cd5c).
This runtime subtree does not contain the upstream host applications or docs;
their source attribution does not require installing ZoomPilot on the comma.

Jetlink is experimental. Use separate power and USB 3, set up parked, and verify
StarPilot's active model status. See the local guide for recovery and limitations.

## Attribution

Jetlink was developed by Zeph Leggett / ZoomPilot. Copyright (c) 2026 Zeph Leggett.
The original [MIT license](LICENSE) is preserved without modification.
[Upstream README and credits](https://github.com/zoompilot/jetlink/blob/c17cd5c/README.md).
