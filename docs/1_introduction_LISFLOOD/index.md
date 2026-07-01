## About LISFLOOD

LISFLOOD is a spatially distributed, physically based, hydrological rainfall-runoff-routing model that has been developed by the Joint Research Centre (JRC) of the European Commission since 1997. 
Since then, LISFLOOD has proven to be suitable for a variety of applications, including flood simulation and forecasting; water resources assessment; analysis of the impacts of land use changes; river regulation measures, and other water management plans; climate change analysis.
Its most prominent application is probably within the [European Flood Awareness System, EFAS](https://european-flood.emergency.copernicus.eu/react) and the [Global Flood Awareness System, GloFAS](https://global-flood.emergency.copernicus.eu/react/)
operated under [Copernicus Emergency Management System, CEMS](https://emergency.copernicus.eu/).

Its wide applicability is due to its modular structure as well as its temporal and spatial flexibility. 
The user can control the model inputs and outputs and the selection of the model modules.
The model can be extended with additional modules when need arises, to satisfy the new target objective. 
At the same time the model has been designed to be applied across a wide range of spatial and temporal scales. 
OS LISFLOOD is grid-based, and applications so far have employed grid cells of as little as 100 metres for medium-sized catchments, and up to kilometer scale for continental and global applications. 
OS LISFLOOD can be used to generate long-term water balance simulations (climatology runs, with hourly to daily time steps), as well as individual flood events (with hourly to daily time steps). 

Although LISFLOOD's primary output product is channel discharge, all internal rate and state variables (soil moisture, for example) can be written as output as well.
All output can be written as grids, or time series at user-defined points or areas. The user has complete control over how output is written, thus minimising any waste of disk space or CPU time.

LISFLOOD is implemented in Python high level language: the users are recommended to refer to the chapter [Installation of the LISFLOOD model](../2_installation/index.md) and to the readme of the [OS LISFLOOD GitHub repository](https://github.com/ec-jrc/lisflood-code#lisflood-os) to find detailed information on requirements and installation protocol.

[🔝](#top)
