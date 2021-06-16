# Channel geometry

In the LISFLOOD model flow through the channel is simulated using the kinematic wave equations. Channel maps describe the sub grid information of the channel geometry, i.e. the length, slope, width and depth of the main channel inside a grid-cell.  <br/>
+ The **channel mask** map is the Boolean field with '1' for all grid-cells with channels and NoData for all grid-cells with no channels.  <br/>
+ The **channel side slope** map (referred as 's' in Figure 41) defines the slope of the channel banks. <br/>
+ The **channel length** map is the length of the river in each grid-cell, and the value can exceed grid-size to account for meandering rivers. <br/>
+ The **channel gradient** (or channel slope) map is the average gradient of the main river inside a cell. <br/>
+ The **Manning's roughness coefficient** map can be derived by an empirical relationship of the DEM and the upstream area according to [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf). The kinematic wave approach uses the Manning’s formula, an empirical formula for open channel flow or free-surface flow driven by gravity. The Manning’s roughness coefficient is reciprocal proportional to the cross-sectional average velocity (in m/s). A lower Manning’s coefficient results in a faster responding time at the outlet. <br/>
+ The **bottom width map** (referred as Wb in Figure 41) is the width of the bottom of the channel. <br/>
+ The **floodplain map** (referred as Wfp in Figure 41) is used to calculate water levels in the LISFLOOD model. <br/>
+ The **bankfull channel depth** map (referred as Dbf in Figure 41) is the difference between floodplain bottom level (referred as zfp in Figure 41) and the channel bottom level (referred as zbot in Figure 41. <br/>
Channel characteristics, explained above, are shown in the Figure 41 below.  <br/>

<p float="left">
  <img src="../media/Static-Maps/channel_geometry1.png" width="600" />
  <img src="../media/Static-Maps/channel_geometry2.png" width="400" /> 
</p>
*Figure41: Geometry of channel cross-section in kinematic wave routing (original figure from [Burek et al., 2013](https://publications.jrc.ec.europa.eu/repository/handle/JRC78917)).

## General map information and possible source data

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

## Methodology

### Channel mask (chan)
The channel mask map is used to identify the cells that have channels. The grid-cells that have a channel length (see chanlength map creation below) above zero are assigned to the Boolean field '1', the grid-cells that have a channel length below or equal to zero are assigned with NoData.

### Side slope (chans)
The channel side slope map is calculated by dividing the horizontal distance (referred as 'dx' in Figure 42) by vertical distance (referred as 'dy' in Figure 42); here ‘1’ was assigned to all the grid cells, which correspond to a 45° angle of the side slope.

### Channel length (chanlenght)
The channel length map (in meters) can be created by using the 'rivlen' layers from the CaMa-Flood dataset (for more information see the FLOW method of Yamazaki, link), multiplied by the LISFLOOD model mask.

### Channel gradient (changrad)
To compute the channel gradient map, the absolute difference (in meters) of the elevation between two grid-cells is first calculated by using i) the local drain direction (ldd) map to extract the connectivity between grid-cells, and ii) the channel length of the upstream grid-cell:<br/>
$$
elevationDifference = elevation_{upstreamCell} - elevation_{downstreamCell}.
$$
Then, the channel gradient is computed and assigned to the upstream grid-cell:
$$
changrad=\frac{elevationDifference}{chanlength}
$$
$changrad$ is set equal 0 where $ldd$ is 5.

### Manning's roughness coefficient (chanman)
The Manning's roughness coefficient for channels can be derived by an empirical relationship between the elevation (in $m$) of the grid-cell and its upstream area (in $km^2$) following [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf):
$$
chanman = 0.025 + 0.015 * minimum(\frac{50}{upstreamArea} , 1) + 0.30 * minimum(\frac{elevation}{2000} , 1).
$$

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
