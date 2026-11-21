#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
version="$(docker info --format '{{.ServerVersion}}')"
case "$version" in
  [0-9]*.[0-9]*) ;;
  *) echo 'Docker engine is not ready.' >&2; exit 1 ;;
esac
missing=0
for image in dermascope-backend:e38-cpu-v1 dermascope-frontend:dev-v1; do
  docker image inspect "$image" >/dev/null 2>&1 || missing=1
done
if [ "$missing" = 1 ]; then
  bundle="${1:-docker/bundles/dermascope-images.tar}"
  if [ ! -f "$bundle" ]; then
    echo "Obtain the prebuilt dermascope-images.tar bundle; no separate weights are needed." >&2
    exit 1
  fi
  docker image load -i "$bundle"
fi
docker compose up -d --wait --wait-timeout 360
echo 'Website: http://localhost:5180'
