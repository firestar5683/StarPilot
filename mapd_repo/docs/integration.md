# openpilot Integration

## Minimal
1. Add capnp definitions to cereal.
    * In openpilot cereal/custom.capnp replace CustomReserved17-19 with the Mapd
      types and structs in cereal/custom/custom.capnp line 65 to the end.
    * In openpilot cereal/log.capnp replace customReserved17-19 in the Event
      struct with the mapd types.
      ```
      mapdExtendedOut @143 :Custom.MapdExtendedOut;
      mapdIn @144 :Custom.MapdIn;
      mapdOut @145 :Custom.MapdOut;
      ```
2. Add mapdOut as a service in openpilot cereal/services.py
   ```python
   "mapdOut": (True, 20., 20, QueueSize.MEDIUM),
   ```
3. Add MapdSettings to openpilot common/params\_keys.h
   ```c++
    {"MapdSettings", {PERSISTENT, JSON}},
   ```
4. Add mapd binary to openpilot selfdrive directory
5. Add mapd to openpilot system/manager/process\_config.py
   ```python
   NativeProcess("mapd", "selfdrive", ["./mapd"], always_run),
   ```
5. In openpilot selfdrive/controls/plannerd.py add mapdOut to SubMaster
6. In openpilot selfdrive/controls/lib/longitudinal\_planner.py add the
   following code right before the force\_slow\_decel if statement:
   ```python
   if sm.valid['mapdOut']:
     if sm['mapdOut'].suggestedSpeed > 0 and v_cruise > sm['mapdOut'].suggestedSpeed:
       v_cruise = sm['mapdOut'].suggestedSpeed
   ```
7. ssh into the comma device with a running mapd instance and run
   `./selfdrive/mapd i` to download maps and configure mapd.

## Advanced
mapd offers a lot more data and options to allow for customization of behavior
outside of the basic example above as well as outputs for use in the openpilot
ui. The outputs are described in detail in outputs.md. Inputs for controlling
mapd behavior are described in detail in inputs.md. There are also built in
defaults, including settings and map download areas, that can be overriden as
described in overriding-internal-defaults.md.

In general I'd suggest integrating mapd into your openpilot fork in the way you
desire your fork to work, and not exposing many of the options available in
mapd. However, if you extend mapd functionality I suggest always having a way to
enable mapd in the simple integration described above that allows for advanced
users to set the mapd options and use the built in mapd behavior if they so
wish. mapd provides a terminal ui that allows a user to configure all of its
advanced settings, so an advanced user can ssh in and use that to configure mapd
in ways not provided or officially supported by your openpilot fork. This also
means that if you have additional toggles for map features outside of the mapd
settings that I would suggest trying to ensure your ui still displays mapd
outputs when those additional toggles are disabled, this allows for those
advanced user to still see at least some basic information about how mapd is
operating if they choose to use the built in options as opposed to the fork
options. But, don't sacrifice your fork functionality in pursuit of this so that
there's still variety in the ideas and operation of various forks.

If you have a feature for different map behavior than what mapd provides
built-in, please consider reaching out to see if it can be added directly to
mapd. One goal with this version of mapd is to provide many different behavior
options for its users, so adding additional options is welcome.

Some core things most forks will want to implement in their UI include: A
download menu with download progress, toggles for enabling functionality,
display of mapd outputs including speed limits, suggested speed, and road name.

For the download menu, I suggest making your ui dynamic based off of the
download areas json. Ideally make a copy of settings/download\_menu.json and
place it in the root of your openpilot fork with the name
mapd\_download\_menu.json. mapd will then use your copy and any modifications
you make to it when you trigger downloads as long as you follow the schema
described in ovverriding-internal-defaults.md. One thing I don't want to
personally support is updates to the default download menu, so if you want
additional areas to be included the best way is to maintain your own override
file as described, and you can generally expect there to not be any updates to
the file included in this mapd repo. The download progress output is part of the
mapdExtendedOut cereal message and is described in outputs.md.

For toggles, if the functionality is built-in to mapd you can control the
mapdSettings through mapdIn messages as described in inputs.md. Each setting
also has a corresponding key in the MapdSettings param json that is described in
settings.md. You can change the defaults for the mapd settings by providing a
custom defaults json as described in overriding-internal-defaults.md.

Common outputs for use in the openpilot ui will be part of the MapdOut cereal
message as described in outputs.md. The most common values used for the ui will
likely be speedLimit, roadName, and suggestedSpeed which are explained in more
detail in outputs.md. Some other outputs that are often of interest would be
nextSpeedLimit, nextSpeedLimitDistance, and speedLimitAccepted which are also
further described in outputs.md.

If you want to have completely custom trigger logic for upcoming curves, mapd
still outputs the suggested velocities/estimated curvature paths. The path
output for those values is part of the MapdExtendedOut cereal message and is
described in detail in outputs.md.
