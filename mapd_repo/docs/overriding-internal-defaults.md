# Overriding Internal Defaults

Mapd contains built in default and recommended settings, as well as a default
download menu file. The source files exist as json files in the settings folder
of the source code. They get built into the mapd binary during compile time and
are thus not directly editable. Instead, mapd will look for custom versions of
these files in the following paths:
* defaults.json: /data/openpilot/mapd\_defaults.json
* recommended.json: /data/openpilot/mapd\_recommended.json
* download\_menu.json: /data/openpilot/mapd\_download\_menu.json

## Default and Recommended Settings
Before loading custom default settings mapd will always load the
built in default settings. This ensures that any values missing from the custom
default settings will still have an appropriate default value set.

Custom defaults.json and recommended.json files should include a
`settings_version` field matching mapd's current settings schema (see
settings.md for the version and the nested json shape it expects, e.g.
`speed_limit`, `logger`, and `personalities` objects). If a custom file has an
older `settings_version` mapd automatically migrates it to the current schema
before applying it, so existing overrides do not need to be rewritten
immediately, but new overrides should target the current schema directly.

When mapd starts, it will always load the default settings before trying to load
the saved values in the params. This ensures that any new values that were not
previously saved will load with a default value. The same logic as above applies
on this first load. Mapd will load the internal defaults, then mapd will load
the custom defaults over top of the internal defaults, and finally mapd will
load the saved settings in the MapdSettings param over top of the loaded
defaults.

Recommended settings are applied overtop of the currently set values. This means
that any values not contained in the recommended settings will remain their
existing values when the recommended settings are loaded. If those values are
never set this implies that they will use the default values as the default
values are always loaded upon starting mapd.

## Download Menu
The download menu file is used for two purposes. When triggering a download, the
area names given to mapd are used to locate the appropriate bounding box from
the download menu file. The download menu file is also used to create a dynamic
menu in the mapd cli for selecting areas to download. This means that additional
areas not provided by mapd can be added as options for downloads by copying the
download\_menu.json to /data/openpilot/mapd\_download\_menu.json and then adding
any desired areas to the file. The structure is as follows:
```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "additionalProperties": {"$ref": "#/definitions/area_menu"},
  "definitions": {
    "area_menu": {
      "type": "object",
      "additionalProperties": {"$ref": "#/definitions/area"},
    },
    "area": {
      "type": "object",
      "properties": {
        "full_name": {
          "type": "string"
        },
        "bounding_box": {
          "type": "object",
          "properties": {
            "min_lon": {
              "type": "number"
            },
            "min_lat": {
              "type": "number"
            },
            "max_lon": {
              "type": "number"
            },
            "max_lat": {
              "type": "number"
            }
          },
          "required": [
            "min_lon",
            "min_lat",
            "max_lon",
            "max_lat"
          ]
        },
        "submenu": {
          "type": "string"
        }
      },
      "required": [
        "full_name",
        "bounding_box"
      ]
    }
  }
}
```

Note the optional submenu value in an area. The submenu value allows for
chaining of the menus when requesting a download, so the submenu value should
exactly match a top level key in the main object. This value is not used by the
cli tui however, so selecting an entry with a submenu in the tui will just
result in that entry being downloaded.
