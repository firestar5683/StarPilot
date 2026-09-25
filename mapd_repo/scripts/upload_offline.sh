#!/bin/bash

rclone copy offline r2:osm-map-data/offline/ --progress --include **/*.tar.gz
