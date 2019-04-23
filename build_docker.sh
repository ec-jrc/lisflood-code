#!/usr/bin/env bash

docker build -t efas/lisflood:latest .
docker tag efas/lisflood:latest index.docker.io/efas/lisflood:latest
