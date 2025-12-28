#!/bin/bash

version=0.3.21-test

rm -rf ./web/dist/

# 测试版本推送到我们自己的仓库 只支持 x86-64
docker build -t iteam-harbor.seeed.cn/sensecraft-solutions/sensecraft-indoor-positioning:$version -f Dockerfile-local .
docker push iteam-harbor.seeed.cn/sensecraft-solutions/sensecraft-indoor-positioning:$version

docker build -t iteam-harbor.seeed.cn/sensecraft-solutions/sensecraft-indoor-positioning-remote:$version -f Dockerfile-remote .
docker push iteam-harbor.seeed.cn/sensecraft-solutions/sensecraft-indoor-positioning-remote:$version


#
#docker build -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-local -f Dockerfile-remote .
#docker build -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning -f Dockerfile-local .

#docker buildx build --platform linux/amd64 -t seeedcloud/sensecraft-indoor-positioning:$version -t seeedcloud/sensecraft-indoor-positioning --push -f Dockerfile-local .
#docker buildx build --platform linux/amd64,linux/arm64 -t seeedcloud/sensecraft-indoor-positioning-remote:$version -t seeedcloud/sensecraft-indoor-positioning-remote --push -f Dockerfile-remote .

#docker push seeedcloud/sensecraft-indoor-positioning:$version
#docker push seeedcloud/sensecraft-indoor-positioning
#
#docker push seeedcloud/sensecraft-indoor-positioning-remote:$version
#docker push seeedcloud/sensecraft-indoor-positioning-remote