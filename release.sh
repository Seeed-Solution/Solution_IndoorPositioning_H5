#!/bin/bash

version=0.0.5
#
docker build -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning:latest .

docker push seeedcloud/sensecraft-indoor-positioning:$version
docker push seeedcloud/sensecraft-indoor-positioning:latest

