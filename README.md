# StarPilot

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/firestar5683/StarPilot)
[![Discord](https://img.shields.io/discord/1387432184121393333?label=Discord)](https://firestar.link/discord)
[![Last Updated](https://img.shields.io/github/last-commit/firestar5683/StarPilot/StarPilot)](https://github.com/firestar5683/StarPilot)
[![Wiki](https://img.shields.io/badge/Wiki-StarPilot-blue?logo=wiki)](https://wiki.firestar.link)

**StarPilot** is a custom fork of [comma.ai's openpilot](https://comma.ai/openpilot),
an open source driver assistance system.


Openpilot provides
* Automated Lane Centering
* Adaptive Cruise Control
* Lane Change Assist
* Driver Monitoring *without wheel nags*

StarPilot was formerly a GM targeted fork,
but [has expanded to offer Quality-Of-Life improvements for all](#features)!

StarPilot is built off of [FrogPilot](https://github.com/FrogAi/FrogPilot)
and supports the major features FrogPilot offers.

StarPilot has a vibrant, welcoming community [discord](https://firestar.link/discord).
Stop by to chat or ask questions!

## Documentation

Please see [https://wiki.firestar.link](https://wiki.firestar.link) for hardware lists,
installation guides, and software configuration.

## Features

* Full support for Comma C3, C3X, and C4
* Model switcher with all of comma's tinygrad driving models
* Special longitudinal planner tuning for VoACC (visual only, radar-less) vehicles
* Custom-tuned torque controllers for an expanding list of cars.
* Galaxy: StarPilot's portal to configure your comma device using your phone from anywhere.
Download models, change settings, update software, visualize live model outputs for tuning.
* Always On Lateral (full time steering assist)*
* Speed Limit Controller*
* Learning Curve Speed Controller*
* Conditional Experimental Mode (CEM)*
* Driving Profiles*
* Custom themes*
* Alert Volume Controller*
* Comma Pedal Interceptor support*
* Toyota SDSU support*
* ZSS support*
* High quality dashcam recordings*
* Enhanced tuning for CEM (dynamic experimental mode switching)
* And more!

\* [Inherited from FrogPilot](https://github.com/FrogAi/FrogPilot#openpilot-vs-frogpilot)

## GM-only Features

* Increased LKAS fault resiliency
* ASCM_INT and SASCM support
* Custom lateral torque controller, with special tuning for Bolts
* 50% extra torque on 2017 Chevy Bolt
* Improved lateral and longitudinal tuning
* Dashboard cruise control display speed spoofing for vehicles with pedal interceptor
* Extra steering wheel button functionality for vehicles with pedal interceptor
* Optional toggle to boot comma when remote starting your vehicle

## Developer Features

* Native and cross compilation for Windows, Mac, and Ubuntu
* Custom AGNOS to support C3, C3X, and C4
* To run UI on PC:
  * `./c3` for large UI
  * `./c4` for small UI
* `./build` to produce cross compiled binaries for comma devices.
Uses your comma's sysroot/toolchain
* Toggle: "Use Precompiled Binaries" to allow switching between fast boot / editable builds
* Custom long maneuver tests, specifically designed for regen-only vehicles

## Third-Party Notices
* Portions of this software include modified versions of the Material Design Icons provided by Google under the Apache License 2.0. A copy of the license is included in the `LICENSE-MDI` file.
