## Channel geometry

In the LISFLOOD model flow through the channel is simulated using the kinematic wave equations. Channel maps describe the sub grid information of the channel geometry, i.e. the length, slope, width and depth of the main channel inside a grid-cell.  <br/>
The channel mask map is the Boolean field with '1' for all grid-cells with channels and NoData for all grid-cells with no channels.  <br/>
The channel side slope map (referred as 's' in Figure 41) defines the slope of the channel banks. <br/>
The channel length map is the length of the river in each grid-cell, and the value can exceed grid-size to account for meandering rivers. <br/>
The channel gradient (or channel slope) map is the average gradient of the main river inside a cell. <br/>
The Manning's roughness coefficient map can be derived by an empirical relationship of the DEM and the upstream area according to Burek et al. (2014). The kinematic wave approach uses the Manning’s formula, an empirical formula for open channel flow or free-surface flow driven by gravity. The Manning’s roughness coefficient is reciprocal proportional to the cross-sectional average velocity (in m/s). A lower Manning’s coefficient results in a faster responding time at the outlet. <br/>
The bottom width map (referred as Wb in Figure 41) is the width of the bottom of the channel. <br/>
The floodplain map (referred as Wfp in Figure 41) is used to calculate water levels in the LISFLOOD model. <br/>
The bankfull channel depth map (referred as Dbf in Figure 41) is the difference between floodplain bottom level (referred as zfp in Figure 41) and the channel bottom level (referred as zbot in [Figure 41](#fig:Figure41). <br/>
Channel characteristics, explained above, are shown in the Figure 41 below.  <br/>



```{r Figure41, fig.height=2.4, fig.width= 2.5, fig.cap="Figures work nicely", echo = FALSE}
<p float="left">
  <img src="../media/Static-Maps/channel_geometry1.png" width="600" />
  <img src="../media/Static-Maps/channel_geometry2.png" width="400" /> 
</p>
```
### Leaf Area Index for land covers forest, irrigated crops, and other

#### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
| LAI for forest        |  laif.nc; Float32          | Units: -; Range: 0 ..7         |10-day average (36 maps in total) Leaf Area Index for closed forested areas (forest fraction per grid-cell ≥ 0.7)|
| LAI for irrigated crops  | laii.nc; Float32    | Units: -; Range: 0 ..7     |10-day average (36 maps in total) Leaf Area Index for irrigated crop areas (irrigated crop fraction per grid-cell ≥ 0.7)|
| LAI for other     | laio.nc; Float32       | Units: -; Range: 0 ..7     |10-day average (36 maps in total) Leaf Area Index for mainly other land cover type areas (other land cover type fraction per grid-cell ≥ 0.7)|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
| Copernicus Global Land Service LAI Collection Version 2 | https://land.copernicus.eu/global/products/lai | 1 January 2010 - 31 December 2019 | Global, 1 km|
| Fraction of forest | It can be prepared by using the methodology of section XXX| NA | Global, 1' and 3'|
| Fraction of irrigated crops | It can be prepared by using the methodology of section XXX| NA | Global, 1' and 3'|
| Fraction of other land cover type | It can be prepared by using the methodology of section XXX| NA | Global, 1' and 3'|

#### Methodology

To create LAI for forest, irrigated crops and other land cover type, maps [Copernicus Global Land Service LAI Collection](https://land.copernicus.eu/global/products/lai) Version 2 can be used.<br/> The dataset provides a 10-day average LAI information, 36 maps each year. Here, to normalise the climate over different regions of the globe, the 10-day average LAI maps are aggregated over a 10-year period (i.e. first 10-day average of years 2010-2019 are aggregated to compute a first 10-day climatological average). As a result 36 climatological LAI maps are calculated. 
Then, fraction maps for forest, irrigated crops, and other land cover type are used to mask non-dense areas of the land cover type in question (i.e. fraction is less than 0.7) over the climatological LAI maps. <br/>
The LAI map resolution of the resulting field is reduced from native to the required one (e.g. from 1 km to 1 arc min) as follows. Firstly, the resolution is reduced to 1, 3, 15 arc min and 1, 3, 15, 60 degrees with mean.unweighted() reducer, and then all different resolutions are assembled to create a field with no missing values. For each resolution (going from the highest to the coarsest), grid-cells with missing values are identified and filled with the value of the corresponding grid-cell with non-missing value from the next resolution down map (e.g. using 3 arc min to fill in 1 arc min missing values). If the corresponding grid-cell is masked (has a missing value), then the value of the corresponding non-masked grid-cell from the next resolution down map is used, until all resolution maps are explored. If the corresponding grid-cell value of the coarsest resolution (here 60 degree) is still missing, a zero value is given.

#### Results (examples)



<p float="left">
  <img src="../media/Static-Maps/laif_0105_European_01min.png" width="394" />
  <img src="../media/Static-Maps/laif_0105_Global_03min.png" width="611" /> 
</p>

*Figure 51: Leaf area index for forest 5th January map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*


<p float="centre">
  <img src="../media/Static-Maps/laif_0805_European_01min.png" width="394" />
  <img src="../media/Static-Maps/laif_0805_Global_03min.png" width="611" /> 
</p>

*Figure 52: Leaf area index for forest 5th August map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*
