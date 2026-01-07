#!/bin/bash

version=0.4.0

rm -rf ./web/dist/

docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning --push -f Dockerfile-local .
docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-remote --push -f Dockerfile-remote .
