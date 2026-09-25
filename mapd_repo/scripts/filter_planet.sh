#!/bin/bash
osmium tags-filter planet-daily.osm.pbf "nw/highway=motorway,trunk,primary,secondary,tertiary,unclassified,residential,motorway_link,trunk_link,primary_link,secondary_link,tertiary_link" -o filtered.osm.pbf --overwrite
