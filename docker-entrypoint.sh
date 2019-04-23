#!/usr/bin/env bash

set -e
#if [[ "$1" = 'usecases' ]]; then
#    mkdir -p /input/cordex
#    mkdir -p /input/efas
#    mkdir -p /input/basemaps
#    echo "Copying basemaps to /input/..."
#    cp /basemaps/* /input/basemaps/
#    echo "copy input files to /input/cordex......"
#    cp /tests/data/input/cordex/*.nc /input/cordex/
#    cp /tests/data/tests_cordex.xml /input/
#    echo "copy input files to /input/efas......"
#    cp /tests/data/input/efas/*.nc /input/efas/
#    cp /tests/data/tests_efas.xml /input/
#    chmod a+w /input/*.xml
#else
#    exec python /lisflood/lisf1.py "$@"
#fi
exec python /lisflood/lisf1.py "$@"
