#!/bin/bash

mkdir -p ~/.config/rclone

cat > ~/.config/rclone/rclone.conf <<- EOM
[r2]
type = s3
provider = Cloudflare
access_key_id = $ACCESS_KEY_ID
secret_access_key = $SECRET_ACCESS_KEY
region = auto
endpoint = $ENDPOINT
acl = private
EOM
