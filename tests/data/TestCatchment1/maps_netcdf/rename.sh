#!/bin/sh

for file in *_tr.nc
do
    mv -i "${file}" "${file/_tr.nc/.nc}"
    
done
