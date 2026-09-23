#!/usr/bin/env bash
set -u
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl unzip ca-certificates >/dev/null
ZIP='/work/tools/osm2world/OSM2World-latest-bin.zip'
CUR='/work/tools/osm2world/current'
URL='https://osm2world.org/download/files/latest/OSM2World-latest-bin.zip'

mkdir -p "$(dirname "$ZIP")"
rm -f "$ZIP"

echo "Docker DNS test for osm2world.org:"
getent hosts osm2world.org || true

if curl -L --fail --retry 3 --retry-delay 2 -o "$ZIP" "$URL"; then
  if [ "$(stat -c%s "$ZIP" 2>/dev/null || echo 0)" -gt 300000000 ]; then
    rm -rf "$CUR"
    mkdir -p "$CUR"
    unzip -q "$ZIP" -d "$CUR"
    echo "OFFICIAL_DOWNLOAD_OK"
    exit 0
  fi
fi

echo "OFFICIAL_DOWNLOAD_FAILED"
exit 9
