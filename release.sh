#!/bin/bash

version=0.3.4

rm -rf ./web/dist/

docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning --push -f Dockerfile-local .
#docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-remote --push -f Dockerfile-remote .
