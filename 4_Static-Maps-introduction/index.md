# USER GUIDE FOR THE CREATION OF THE INPUT MAP DATASET

## About this user guide

This user guide provides instructions and examples to create static maps required as an input for LISFLOOD hydrological model.<br>
The examples in this user guide have been derived from the generation of the static input maps for the European and Global Flood Awareness Systems (EFAS and GloFAS) of the Copernicus Emergency Management Service. Users are encouraged to create their own static maps for their region of interest and using local, national or any other type of source data. Possible data sources, used as examples in this user guide, are listed in the [Appendix A](../4_Static-Maps_Appendix).<br>
Maps can be elaborated with any GIS/remote sensing software. Examples in this guide have been performed using CDO, GDAL, Python, and Google Earth Engine platform.<br>

## Projection and file type

All static input maps for LISFLOOD need to have the same model domain, projection, resolution – same number of columns and rows, and same grid of coordinates (i.e. all 4 corners of each pixel must have exactly the same coordinates in degrees or in meters, depending on the reference system). This is a strict requirement of the [LISFLOOD model](https://github.com/ec-jrc/lisflood-code) (here and below ‘the LISFLOOD model’ refers to the version 3.1.0) that at present cannot accept input maps at different spatial resolution or geographical extension.<br>
All maps should be introduced in the model in NetCDF or PCRaster file format.
This user guide provides the examples for the European and Global domains that are being used in EFAS and GloFAS models, respectively. The static fields structure for EFAS and GloFAS is the following:<br>

+ Projection EPSG:4326 - WGS84: World Geodetic System 1984;
+ Examples of horizontal resolution: 1' (~1.86 km at the Equator) and 3' (~5.57 km at the Equator);
+ Examples of coverage and horizontal resolution: a) global domain: North = 90.00 N; South = 90.00 S; West = 180.00 W; East = 180.00 E; file size in grid-cells: 03' = 7200x3600; b) European domain: North = 72.25 N; South = 22.75 N; West = 25.25 W; East = 50.25 E; file size in grid-cells: 01' = 4530x2970; 
+ NoData value: 1) for Byte (Int8) files = 0; 2) for Real (Float32) files = -999999.0.
+ Ocean masked with NoData (except, pixel length and pixel area maps).


### Authors of the version compiled in May 2021
Margarita Choulga, Francesca Moschini, Christel Prudhomme, Cinzia Mazzetti and ECMWF team

#### Acknowledgements
The authors thank Juliana Disperati (JRC), Stefania Grimaldi (JRC), Peter Salamon (JRC) and Ad De Roo (JRC) for invaluable help with examining the upgraded static map and guidance throughout the work and preparation of this user guide; Dai Yamazaki (The University of Tokyo) and Emanuel Dutra (IPMA) for useful discussions and comments; Damien Decremer (ECMWF) for expert help with file transformation technical work. <br>
Margarita Choulga, Francesca Moschini, Christel Prudhomme, and Cinzia Mazzetti were funded by Copernicus Emergency Management Service – Early Warning Systems – operational computational centre of EFAS (CEMS-Flood) project which received funding from European Commission Copernicus Emergency Management Service (CEMS) Framework Contract No 198702 awarded to ECMWF.


