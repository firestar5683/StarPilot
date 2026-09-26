# StarPilot

StarPilot is an independent fork of [openpilot](https://github.com/commaai/openpilot), with custom driving controls, vehicle integrations, raylib interfaces for comma 3 and comma four, and the Galaxy companion interface.

**Domathon is the development branch for StarPilot 7.0.** It rebuilds StarPilot on a current openpilot foundation. Feature migration and vehicle qualification are still in progress; this branch is not a completed replacement for the existing Dom release.

## Explore the project

- [Developer commands](tools/STARPILOT_DEVELOPMENT.md): host tools, replay, and device builds.
- [Driving interfaces](openpilot/starpilot/ui/README.md) and [Galaxy](openpilot/starpilot/galaxy/README.md): native and companion controls.
- [Driving models](openpilot/starpilot/models/README.md): model management, artifact compatibility, and Model Laboratory status.
- [Builds and developer tools](docs/how-to/laptop-device-build.md): local development and device builds.
- [Dependency maintenance](tools/vendor/README.md): tracked source folders and upstream sync records.

## Development

Dependencies are included as ordinary source folders. No recursive submodule checkout is needed. [upstream-sync.json](upstream-sync.json) records the openpilot baseline and the source revisions used for vendored dependencies.

The familiar development entry points are retained:

| Command | Purpose |
| --- | --- |
| `./build` | Build the device software using the matching AGNOS environment |
| `./build --panda` | Build the supported Panda firmware targets |
| `./c3` | Open the comma 3 interface on a development host |
| `./c4` | Open the comma four interface on a development host |
| `./onroad` | Open the onroad development view |
| `./dev` | Use the isolated host development environment |

See the [build guide](docs/how-to/laptop-device-build.md) for setup, prerequisites, and target-specific behavior. The [UI guide](openpilot/starpilot/ui/README.md) describes desktop previews and their limits.

## Testing and vehicle support

StarPilot retains upstream vehicle and Panda safety interfaces and adds regression coverage for its custom behavior. The [safety workflow](.github/workflows/safety.yaml) and feature tests cover distinct parts of the system. A passing interface test, model comparison, or bench run does not establish driving support for every configuration.

Support depends on the vehicle configuration and enabled feature. An existing vehicle identifier or settings page does not by itself establish driving support. Model Laboratory currently exposes management controls, but paired driving inference remains unavailable pending integration and Chestnut validation.

## Upstream and attribution

The current openpilot baseline is [`78dccf0b482ea1298fd1f6fa59b0554187b02ce6`](https://github.com/commaai/openpilot/commit/78dccf0b482ea1298fd1f6fa59b0554187b02ce6). Its history remains intact, followed by the StarPilot foundation and feature commits. Upstream development continues independently; the baseline changes only after an update has been integrated and checked.

See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and [CREDITS.md](CREDITS.md) for licensing and source attribution. Component licenses remain with their source folders. StarPilot is maintained independently of comma.
