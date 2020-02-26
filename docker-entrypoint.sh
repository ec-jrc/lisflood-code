#!/usr/bin/env bash

set -e
if [[ "$1" = 'usecases' ]]; then
    # copy test data to a folder that is mapped to host computer
    mkdir -p /usecases
    echo "Copying test catchments to /usecases/..."
    cp -R /tests/data/TestCatchment /usecases/
    cp -R /tests/data/TestCatchmentWithLakes /usecases/
    cp -R /tests/data/static_data /usecases/
    cp -R /tests/data/settings/full_with_lakes.xml /usecases/TestCatchmentWithLakes/
    chmod a+w /usecases/TestCatchment/settings/*.xml
    chmod a+w /usecases/TestCatchmentWithLakes/*.xml
elif [[ "$1" = 'tests' ]]; then
    # execute unit tests
    exec pytest /tests -x -l -ra
else
    # execute lisflood
    exec python /lisf1.py "$@"
fi
