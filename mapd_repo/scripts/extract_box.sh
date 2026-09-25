#!/bin/bash
min_lon=$((${1}-1))
min_lat=$((${2}-1))
max_lon=$((${3}+1))
max_lat=$((${4}+1))

min_lon=$((${min_lon} < -180 ? -180 : ${min_lon}))
min_lat=$((${min_lat} < -90 ? -90 : ${min_lat}))
max_lon=$((${max_lon} > 180 ? 180 : ${max_lon}))
max_lat=$((${max_lat} > 90 ? 90 : ${max_lat}))

echo "osmium extract --bbox ${min_lon},${min_lat},${max_lon},${max_lat} filtered.osm.pbf -o box.osm.pbf --overwrite"
osmium extract --bbox "${min_lon},${min_lat},${max_lon},${max_lat}" filtered.osm.pbf -o box.osm.pbf --overwrite
