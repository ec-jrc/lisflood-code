## About LISFLOOD

LISFLOOD is a spatially distributed, semi-physical hydrological rainfall-runoff model that has been developed by the Joint Research Centre (JRC) of the European Commission in late 90s. 
Since then, LISFLOOD has been applied to a wide range of applications such as all kind of water resources assessments looking at e.g. 
the effects of climate and land-use change as well as river regulation measures. 
Its most prominent application is probably within the [European Flood Awareness System, EFAS](https://www.efas.eu/en) and the [Global Flood Awareness System, GloFAS](https://www.globalfloods.eu/)
operated under [Copernicus Emergency Management System, EMS](https://emergency.copernicus.eu/).

Its wide applicability is due to its modular structure as well as its temporal and spatial flexibility. 
The model can be extended with additional modules when need arises, to satisfy the new target objective. 
In that sense it can be extended to include anything from a better representation of a particular hydrological flow to the implementation of anthropogenic-influenced processes. 
At the same time the model has been designed to be applied across a wide range of spatial and temporal scales. 
LISFLOOD is grid-based, and applications so far have employed grid cells of as little as 100 metres for medium-sized catchments, to 5000 metres for modelling 
the whole of Europe and up to 0.1° (around 10 km) for modelling globally. Long-term water balance can be simulated (using a daily time step), 
as well as individual flood events (using hourly time intervals, or even smaller). 

Although LISFLOOD's primary output product is channel discharge, all internal rate and state variables (soil moisture, for example) can be written as output as well.
 All output can be written as grids, or time series at user-defined points or areas. 
 The user has complete control over how output is written, thus minimising any waste of disk space or CPU time.

LISFLOOD is implemented in Python and PCRaster Model Framework, wrapped in a Python based interface. 

The Python wrapper of LISFLOOD enables the user to control the model inputs and outputs and the selection of the model modules. 
LISFLOOD runs on any operating system for which Python and PCRaster are available.


[🔝](#top)
