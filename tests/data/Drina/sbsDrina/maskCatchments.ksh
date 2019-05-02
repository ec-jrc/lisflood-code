#!/bin/ksh
#
# Program to mask prescribed catchments
#   D. Decremer - ECMWF - EFAS - PRONEWS (http://www.pronewsprogramme.eu/) - damien.decremer@ecmwf.int | damien.decremer@gmail.com
#
set -eua +xv

if [[ $# -lt 2 ]]; then
  echo
  echo "  Program to automatically mask all but prescribed catchments."
  echo
  echo "  Usage: $0 catchmentNumbers maskedFile <lddFile outletFile boolean offset>"
  echo "    - catchmentNumbers is a stringed list of integers (see example below)"
  echo "    - maskedFile will be a LISFLOOD-compatible pcraster file with masked subcatchments"
  echo 
  echo "    optional arguments (if you provide one, you MUST provide all in order)"
  echo "      - lddFile is a pcraster map"
  echo "          [default = /perm/ma/ma9/xdom/data/staticData/lisflood/ldd.map]"
  echo "      - outletFile is a netCDF map of all outlets in the domain"
  echo "          [default = /perm/ma/ma9/xdom/data/staticData/lisflood/outlets.nc]"
  echo "      - boolean to select mask type"
  echo "          0: returns an integer mask conserving the catchment numbers (0)"
  echo "          1: returns a boolean mask where all selected catchments are set to True (1)"
  echo "          [default = 1]"
  echo "      - offset is an integer used internally to mask outlets. ( > total number of outlets)"
  echo "          [default = 1000000]"
  echo 
  echo "  Examples: "
  echo "    $0 421 ./catchmentsMask.map"
  echo "    $0 \"27 132 502\" ./catchmentsMask.map /perm/ma/ma9/xdom/data/staticData/lisflood/ldd.map /perm/ma/ma9/xdom/data/staticData/lisflood/outlets.nc 0 1000000"
  echo
  echo "             Any comments or suggestions are welcome [damien.decremer@ecmwf.int]"
  echo
  exit 1
else
  catchnums=$1
  set -A catchnums $(echo $catchnums)
  typeset -Z3 catchnums
  maskedFile=$2
  
  lddFile=$3
  if [[ ! -n ${lddFile} ]]; then
    lddFile=/perm/ma/ma9/xdom/data/staticData/lisflood/ldd.map
  fi
  outletFile=$4
  if [[ ! -n ${outletFile} ]]; then
    outletFile=/perm/ma/ma9/xdom/data/staticData/lisflood/outlets.nc
  fi
  boolean=$5
  if [[ ! -n ${boolean} ]]; then
    boolean=1
  fi
  offset=$6 # Should be bigger than the number of outlets
  if [[ ! -n ${offset} ]]; then
    offset=1000000
  fi
fi

module load nco/4.6.7
module load gdal/new
module load cdo/new

## Mask out all outlets except the chosen ones
outlet=$(basename ${outletFile})

# Convert to netCDF 4 format (because it supports type NC_BOOLEAN or NC_BYTE)
ncks -4 ${outletFile} ${outlet}_tmp

# Make type double so we can avoid out-of-range errors when we convert offset to integer
ncap2 -s 'outlets=double(outlets)' ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp

# Make sure to set a non-occuring value as missval
cdo -f nc -setmissval,-9999 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp

# Make all missvals 0. Now the file has only integers saved as double
cdo -f nc -setmisstoc,0 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp

# For each selected catcment, convert to missval, and convert back while adding a big offset
for catchnum in ${catchnums[@]}; do
  cdo -f nc -setctomiss,${catchnum} ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
  if [[ ${boolean} -eq 0 ]]; then
    cdo -f nc -setmisstoc,$((catchnum+offset)) ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
  fi
done

if [[ ${boolean} -eq 1 ]]; then
  # make any non-selected outlets 0
  ncap2 -s 'outlets=outlets-outlets' ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
  # make the selected outlets to 1
  cdo -f nc -setmisstoc,1 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
  # convert all 0 to missing value
  cdo -f nc -setrtomiss,-0.999999,0.999999 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
else
  # Subtract the offset. Now only the selected catchments are in normal range, everything else is either 0 or -offset
  ncap2 -s "outlets=outlets-${offset}" ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
  # Convert these all to missing value. Now the file only has the selected catchments in normal range, the rest is missval
  cdo -f nc -setrtomiss,-${offset},0.999999 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
fi

# Change missing value to 0 for compatibility with pcraster
cdo -f nc -setmissval,0 ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp

if [[ ${boolean} -eq 1 ]]; then
  # Convert type to byte
  ncap2 -s 'outlets=byte(outlets)' ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
else
  # Convert type to NC_INT. This will be turned into VS_NOMINAL in pcraster
  ncap2 -s 'outlets=int(outlets)' ${outlet}_tmp ${outlet}_tmpp && mv ${outlet}_tmpp ${outlet}_tmp
fi

# Convert the netCDF into pcraster format so we can use pcraster functions on it
#   It is crucial that the netCDF data is alreay of type NC_INT or NC_BYTE, because these are
#   the only formats that map to VS_NOMINAL or VS_BOOLEAN, which in turn are the only 
#   formats which pcraster can use the subcatchment function on
gdal_translate -a_srs EPSG:3035 -a_nodata 0 -of PCRaster ${outlet}_tmp C${catchnum}.map
rm -rf ${outlet}_tmp

# Construct python code to call pcraster functions (can also be done in terminal)
cat > maskCatchment.py << EOF
import pcraster as pcr

## --- DEBUG ---
#import numpy as np
#np.set_printoptions(threshold=np.inf)

# Load ldd
ldd = pcr.readmap("${lddFile}")
# Load pixels where catchment must be calculated (as derived above from outlets file)
points = pcr.readmap("C${catchnum}.map")
# Call the pcraster subcatchment function
watershed = pcr.subcatchment(ldd,points)
# Output the result
pcr.report(watershed, "${maskedFile}")

## --- DEBUG ---
#print pcr.pcr2numpy(watershed, 0)
EOF

# run the Python code
python maskCatchment.py

# Clean up
rm -rf maskCatchment.py C${catchnum}.map*

exit 0











# ERROR:
# Warning 1: No UNIDATA NC_GLOBAL:Conventions attribute
# ERROR 6: PCRaster driver: Cannot convert cells: Usetype is not version 2 cell representation, VS_LDD or VS_BOOLEAN
# SOLUTION:
# http://www.gdal.org/frmt_various.html
# PCRaster raster file format
# 
# GDAL includes support for reading and writing PCRaster raster files. PCRaster is a dynamic modeling system for distributed simulation models. The main applications of PCRaster are found in environmental modeling: geography, hydrology, ecology to name a few. Examples include models for research on global hydrology, vegetation competition models, slope stability models and land use change models.
# 
# The driver reads all types of PCRaster maps: booleans, nominal, ordinals, scalar, directional and ldd. The same cell representation used to store values in the file is used to store the values in memory.
# 
# The driver detects whether the source of the GDAL raster is a PCRaster file. When such a raster is written to a file the value scale of the original raster will be used. The driver always writes values using UINT1, INT4 or REAL4 cell representations, depending on the value scale:
# 
# Value scale	Cell representation
# VS_BOOLEAN	CR_UINT1
# VS_NOMINAL	CR_INT4
# VS_ORDINAL	CR_INT4
# VS_SCALAR	CR_REAL4
# VS_DIRECTION	CR_REAL4
# VS_LDD	CR_UINT1
# For rasters from other sources than a PCRaster raster file a value scale and cell representation is determined according to the following rules:
# 
# Source type	Target value scale	Target cell representation
# GDT_Byte	VS_BOOLEAN	CR_UINT1
# GDT_Int32	VS_NOMINAL	CR_INT4
# GDT_Float32	VS_SCALAR	CR_REAL4
# GDT_Float64	VS_SCALAR	CR_REAL4
# The driver can convert values from one supported cell representation to another. It cannot convert to unsupported cell representations. For example, it is not possible to write a PCRaster raster file from values which are used as CR_INT2 (GDT_Int16).
# 
# Although the de-facto file extension of a PCRaster raster file is .map, the PCRaster software does not require a standardized file extension.
# 
# NOTE: Implemented as gdal/frmts/pcraster/pcrasterdataset.cpp.
# 
# See also: PCRaster website at Utrecht University.



