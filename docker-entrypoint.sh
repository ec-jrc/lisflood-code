#!/usr/bin/env bash

set -e
if [[ "$1" = 'usecases' ]]; then
    mkdir -p /usecases
    echo "Copying maps to /input/Drina..."
    cp -R /tests/data/Drina /usecases/
    chmod a+w /usecases/Drina/settings/*.xml
else
    exec python /lisf1.py "$@"
fi
