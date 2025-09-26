#!/bin/bash

version=0.1.4
#
#docker build -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-local -f Dockerfile-remote .
#docker build -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning -f Dockerfile-local .

docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning -f Dockerfile-local .
docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-remote -f Dockerfile-remote .

docker push seeedcloud/sensecraft-indoor-positioning:$version
docker push seeedcloud/sensecraft-indoor-positioning

docker push seeedcloud/sensecraft-indoor-positioning-remote:$version
docker push seeedcloud/sensecraft-indoor-positioning-remote