#!/usr/bin/env bash

docker build -t efas/lisflood:latest .
docker tag efas/lisflood:latest index.docker.io/efas/lisflood:latest
docker tag efas/lisflood:latest d-registry.jrc.it:5000/e1-smfr/lisflood:latest

echo "Lisflood Docker image was built. To push to efas docker repository, first do 'docker login' and then:"
echo "'docker push efas/lisflood:latest' or 'docker push d-registry.jrc.it:5000/e1-smfr/lisflood:latest'"
