#!/bin/bash

rclone copy offline r2:osm-map-data/offline/ --progress --transfers 128 --checkers 128 --exclude **/*.tar.gz
