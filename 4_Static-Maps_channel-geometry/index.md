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
  <img src="../media/Static-Maps/channel_geometry2.png" width="300" /> 
</p>

*Figure41: Geometry of channel cross-section in kinematic wave routing (original figure from [Burek et al., 2013](https://publications.jrc.ec.europa.eu/repository/handle/JRC78917)).*

## General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|         |           |          |
|         |           |          |
|         |           |          |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|         |           |          |
|         |           |          |
|         |           |          |

## Methodology

### Channel mask (chan)
The channel mask map is used to identify the cells that have channels. The grid-cells that have a channel length (see chanlength map creation below) above zero are assigned to the Boolean field '1', the grid-cells that have a channel length below or equal to zero are assigned with NoData.

### Side slope (chans)
The channel side slope map is calculated by dividing the horizontal distance (referred as 'dx' in Figure 42) by vertical distance (referred as 'dy' in Figure 42); here ‘1’ was assigned to all the grid cells, which correspond to a 45° angle of the side slope.

<p float="centre">
  <img src="../media/Static-Maps/channel_geometry3.png" width="350" />
</p>

*Figure 42: Zoom of Figure 41 with highlighted components dx and dy (in red) used to calculate the channel side slope (original figure is from [Burek et al., 2013](https://publications.jrc.ec.europa.eu/repository/handle/JRC78917)).*

### Channel length (chanlenght)
The channel length map (in meters) can be created by using the 'rivlen' layers from the CaMa-Flood dataset (for more information see the FLOW method of Yamazaki, link), multiplied by the LISFLOOD model mask.

### Channel gradient (changrad)
To compute the channel gradient map, the absolute difference (in meters) of the elevation between two grid-cells is first calculated by using i) the local drain direction (ldd) map to extract the connectivity between grid-cells, and ii) the channel length of the upstream grid-cell:<br/>

$$
elevationDifference = elevationUpstreamCell-elevationDownstreamCell.
$$

Then, the channel gradient is computed and assigned to the upstream grid-cell:

$$
changrad=\frac{elevationDifference}{chanlength}
$$

$changrad$ is set equal 0 where $ldd$ is 5.

### Manning's roughness coefficient (chanman)
The Manning's roughness coefficient for channels can be derived by an empirical relationship between the elevation (in $m$) of the grid-cell and its upstream area (in $km^2$) following [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf):

$$
chanman = 0.025 + 0.015 \cdot \min(\frac{50}{upstreamArea} , 1) + 0.30 \cdot \min(\frac{elevation}{2000} , 1).
$$

### Bottom width (chanbw)
The channel bottom width map can be computed using empirical relationship that relate channel width of the grid-cell with its upstream area (in $km^2$); for example, following [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf):<br/>

$$
chanbw = 0.0032 \cdot upstreamArea.
$$

### Floodplain width (Wfp)
The floodplain width (in $m$) can be computed using the following equation from [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf):<br/>

$$
floodplainWidth = 3 \cdot chanbw.
$$

### Bankfull channel depth (chanbnkf)
The channel bankfull depth can be computed in two steps. The first step uses the empirical relationship relating the channel bankfull depth of the grid-cell with its upstream area (in $km^2$) following [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf):<br/>

$$
chanbnkf_{step1} = 0.27 \cdot upstreamArea^{0.33}
$$

The second step uses the Manning's equation following [Burek et al. (2014)](https://ec-jrc.github.io/lisflood/pdfs/Dataset_hydro.pdf). The LISFLOOD model first needs to be run for the calibration period length with the initial channel bottom width and bankfull depth parameters to get a long-term average discharge ($avgdis$) which is then used in the Manning's equation:<br/>

$$
chanbnkf_{step2} = 1.004 \cdot chanman^{0.6} \cdot (2 \cdot avgdis)^{0.6} \cdot chanbw^{-0.6} \cdot changrad^{-0.3}
$$


#### Results (examples)

<p float="left">
  <img src="../media/Static-Maps/chan_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chan_Global_03min.png" width="611" /> 
</p>

*Figure 43: Channel mask map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing the channel pixels.*

<p float="centre">
  <img src="../media/Static-Maps/changrad_European_01min.png" width="394" />
  <img src="../media/Static-Maps/changrad_Global_03min.png" width="611" /> 
</p>

*Figure 44: Channel gradient or slope map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

<p float="centre">
  <img src="../media/Static-Maps/chanman_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chanman_Global_03min.png" width="611" /> 
</p>

*Figure 45: Manning’s roughness coefficient for channels map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

<p float="centre">
  <img src="../media/Static-Maps/chanlength_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chanlength_Global_03min.png" width="611" /> 
</p>

*Figure 46: Channel length map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

<p float="centre">
  <img src="../media/Static-Maps/chanbw_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chanbw_Global_03min.png" width="611" /> 
</p>

*Figure 47: Channel bottom width map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

<p float="centre">
  <img src="../media/Static-Maps/chans_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chans_Global_03min.png" width="611" /> 
</p>
 
*Figure 48: Channel side slope map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing channel side slope (equal to 1) pixel.*
 
<p float="centre">
  <img src="../media/Static-Maps/chanbnkf_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chanbnkf_Global_03min.png" width="611" /> 
</p>

*Figure 49: Bankfull channel depth map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

<p float="centre">
  <img src="../media/Static-Maps/chanflpn_European_01min.png" width="394" />
  <img src="../media/Static-Maps/chanflpn_Global_03min.png" width="611" /> 
</p>

*Figure 50: Channels floodplain width at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*
