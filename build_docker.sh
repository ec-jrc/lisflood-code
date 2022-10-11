#!/usr/bin/env bash

sudo docker build -t jrce1/lisflood:latest .
sudo docker tag jrce1/lisflood:latest index.docker.io/jrce1/lisflood:latest
sudo docker tag jrce1/lisflood:latest d-registry.jrc.it:5000/e1-smfr/lisflood:latest

echo "Lisflood Docker image was built. To push to a repository, first do 'docker login' and then:"
echo "'docker push my.registry.com:5000/myuser/lisflood:latest'"
