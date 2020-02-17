#!/usr/bin/env bash

set -e
if [[ "$1" = 'usecases' ]]; then
    mkdir -p /usecases
    echo "Copying maps to /usecases/TestCatchment/..."
    cp -R /tests/data/TestCatchment /usecases/
    chmod a+w /usecases/TestCatchment/settings/*.xml
else
    exec python /lisf1.py "$@"
fi
