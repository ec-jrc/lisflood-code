# USER GUIDE FOR THE CREATION OF THE INPUT DATASET: MAPS and TABLES 

## About this user guide

This user guide provides instructions and examples to create static maps and text files (commonly referred to as 'tables') required as an input for LISFLOOD hydrological model.<br>
The examples in this user guide have been derived from the generation of the static input maps for the European and Global Flood Awareness Systems (EFAS and GloFAS) of the Copernicus Emergency Management Service. Users are encouraged to create their own static maps for their region of interest and using local, national or any other type of source data. Possible data sources, used as examples in this user guide, are listed in the [Appendix](../4_Static-Maps_appendix).<br>
Maps can be elaborated with any GIS/remote sensing software. Examples in this guide have been performed using CDO, GDAL, Python, and Google Earth Engine platform.<br>

## Projection and file type

All static input maps for LISFLOOD need to have the same model domain, projection, resolution – same number of columns and rows, and same grid of coordinates (i.e. all 4 corners of each pixel must have exactly the same coordinates in degrees or in meters, depending on the reference system). This is a strict requirement of the [LISFLOOD model](https://github.com/ec-jrc/lisflood-code).<br>
All maps should be introduced in the model in NetCDF or PCRaster file format.
This user guide provides the examples for the European and Global domains that are being used in EFAS and GloFAS models, respectively. The static fields structure for EFAS and GloFAS is the following:<br>

+ Projection EPSG:4326 - WGS84: World Geodetic System 1984;
+ Examples of horizontal resolution: 1' (~1.86 km at the Equator) and 3' (~5.57 km at the Equator);
+ Examples of coverage and horizontal resolution: a) global domain: North = 90.00 N; South = 90.00 S; West = 180.00 W; East = 180.00 E; file size in grid-cells: 03' = 7200x3600; b) European domain: North = 72.25 N; South = 22.75 N; West = 25.25 W; East = 50.25 E; file size in grid-cells: 01' = 4530x2970; 
+ NoData value: 1) for Byte (Int8) files = 0; 2) for Real (Float32) files = -999999.0.
+ Ocean masked with NoData (except, pixel length and pixel area maps).


## References

Readers of this user guide are encouraged to cite the scientific publications listed below.

- LISFLOOD Static Maps: Choulga, M., Moschini, F., Mazzetti, C., Grimaldi, S., Disperati, J., Beck, H., Salamon, P., and Prudhomme, C.: Technical note: Surface fields for global environmental modelling, Hydrol. Earth Syst. Sci., 28, 2991–3036, https://doi.org/10.5194/hess-28-2991-2024, 2024.

Nevertheless, it must be noted this user guide provides the most updated and complete documentation about the maps and tables required for the implementation of OS LISFLOOD simulations. 
Users of OS LISFLOOD are encouraged to refer to this online documentation. Inaccuracies and errors can be reported by opening a [GitHub issue](https://github.com/ec-jrc/lisflood-code/issues).

- Pan-European Meterological input data: Salamon, P., Sperzel, T., Gomes, G. R., Radke-Fretz, M., Lemke, C.-D., Russo, C., Schweim, C., Zsoter, E., Dosio, A., Vomero, M., Ziese, M., and Grimaldi, S.: EMO-1: an improved version of the high-resolution multi-variable gridded meteorological dataset for Europe, Earth Syst. Sci. Data Discuss. [preprint], https://doi.org/10.5194/essd-2025-723, in review, 2026



## Available datasets

OS LISFLOOD static input maps and tables for the operational versions of the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/) European and Global Flood Awareness System ([EFAS](https://european-flood.emergency.copernicus.eu/react/), [GloFAS](https://global-flood.emergency.copernicus.eu/react/)) can be downloaded from:

- EC-JRC Data Catalogue, [LISFLOOD static and parameter maps for Europe](https://data.jrc.ec.europa.eu/dataset/f572c443-7466-4adf-87aa-c0847a169f23)

- EC-JRC Data Catalogue, [LISFLOOD static and parameter maps for GloFAS](https://data.jrc.ec.europa.eu/dataset/68050d73-9c06-499c-a441-dc5053cb0c86)

The European Meteorological Observations (EMO) 1 arcmin-resolution, (sub-)daily, multi-variable gridded meteorological dataset includes precipitation, temperature, wind speed,solar radiation and water vapour pressure for the pan-European EFAS computational domain, and it can be downloaded from:

- EC-JRC Data Catalogue, [EMO: A high-resolution multi-variable gridded meteorological data set for Europe](https://data.jrc.ec.europa.eu/dataset/0bd84be4-cec8-4180-97a6-8b3adaac4d26)