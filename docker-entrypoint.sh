#!/usr/bin/env bash

set -e
if [[ "$1" = 'usecases' ]]; then
    # copy test data to a folder that is mapped to host computer
    mkdir -p /usecases
    echo "Copying test catchments to /usecases/..."
    cp -R /tests/data/LF_ETRS89_UseCase /usecases/
    cp -R /tests/data/LF_lat_lon_UseCase /usecases/
    chmod a+w /usecases/LF_ETRS89_UseCase/settings/*.xml
    chmod a+w /usecases/LF_lat_lon_UseCase/*.xml
elif [[ "$1" = 'tests' ]]; then
    # execute unit tests
    exec conda run -n lisflood pytest /tests -x -l -ra
else
    # execute lisflood
    exec conda run -n lisflood python /lisf1.py "$@"
fi
