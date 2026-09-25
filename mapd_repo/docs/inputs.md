# Inputs

Mapd uses cereal messages for communication between openpilot and mapd. For
runtime data inputs mapd will subscribe to standard openpilot cereal services
and does not require any configuration to do so. For inputs specific to mapd the
mapd service subscribes to the mapdIn cereal service. The mapdIn cereal service
should be set to the medium queue size (2mb) in openpilot unless using a version
of openpilot that does not support cereal queue sizes. There are two main types
of things that can be sent through the mapdIn cereal messages, settings and
action triggers.

## MapdIn Message Structure
The MapdIn message is a generic structure that is designed to work for many
different types of inputs without large structure updates to the capnp
definitions. As such it acts as a tagged union where there is a type value that
specifies what action mapd should take and then there are a few generic fields
of different types to handle values for that action. If the setting requires a
number then you would send the data in the float field, a boolean goes in the
boolean field and a string goes in the str field.

Most individual settings additionally have a dedicated type (e.g.
setSpeedLimitOffset), but these are deprecated as of settings\_version 2 in
favor of three generic types: setJsonPathBool, setJsonPathFloat, and
setJsonPathText. For these, put the dot-notation path of the setting within
the MapdSettings json (as documented per-setting in settings.md) into the
jsonPath field, and the value in the matching bool/float/str field.

## Settings
There are two options for configuring mapd settings:
  1. Mapd settings can be configured by updating the MapdSettings param and
  then triggering a reload of the settings in mapd through a cereal message or
  by restarting the mapd service.
  2. Mapd settings can be configured by sending MapdIn cereal messages that
  change the mapd settings in the running process and then can be persisted
  by sending an additional message to persist those values across restarts of
  the service.

Details about the cereal messages for each setting are described in settings.md

There are various actions for loading or persisting the runtime settings that
con be triggered through the MapdIn messages. These actions only require sending
a MapdIn message without any additional data in the message. These message types
are as follows:
  * reloadSettings: Does a full re-initialization of the settings. This includes
    loading the internal default settings, followed by any custom defaults, and
    finally by loading the settings from the MapdSettings param.
  * saveSettings: This action persists all runtime settings values to the
  MapdSettings param.
  * loadDefaultSettings: Loads the internal default settings followed by any
  custom default settings.
  * loadRecommendedSettings: Loads custom recommended settings if available,
  otherwise loads the internal recommended settings. These are applied on top of
  the currently running settings without reapplying the defaults.
  * loadPersistentSettings: This is similar to reloadSettings action, but it
  only loads the MapdSettings param _without_ first loading the default
  settings.

## Map Downloads
Map downloads can be triggered by sending a MapdIn message with the download
type where the value is a path in the download\_menu.json set in the str field.
The path is a period delimited value where the each value is a key name. So, to
download the United States the str value would be "nation.US", or for the state
of Ohio the path would be "us\_state.OH". If a submenu is specified in
download\_menu.json the path can include additional entries that follow the
submenu. With the state of Ohio that means we can also use the value
"nation.US.OH" to download maps for the region. Multiple areas can be triggered
at the same time by simply joining them in the string with a comma. So, to
download Ohio and West Virginia we could use the str value of
"us\_states.OH,us\_states.WV" which will cause mapd to download both states in
that order.

To cancel an in progress download a message with the type cancelDownload can be
sent which will cause mapd to stop downloading files once the current file is
finished downloading.

To get the progress of a download see outputs.md

## Accept Speed Limit
mapd allows for custom logic for accepting a pending speed limit by sending a
message to mapd. A MapdIn cereal message with the type acceptSpeedLimit will
cause mapd to accept the currently pending speed limit.

## Custom Speed Limit
mapd allows for supplying speed limits from custom sources by sending MapdIn
cereal messages. The cereal message should have the type setExternalSpeedLimit
and the speed limit should be supplied in meters/second in the float field.
externalSpeedLimitControl must be enabled in the settings for the values to be
used. You can set the prioritization logic through the speedLimitPriority
setting.
