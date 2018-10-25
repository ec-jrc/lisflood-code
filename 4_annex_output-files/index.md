[//]: # (LISFLOOD output files)


# Output maps

**Table A13.3** LISFLOOD default output maps*           

| **Description** | **Units**       | **File name**   | **Domain**      |
|----------------------|-----------------|------------------|-------------------|
| **AVERAGE RECHARGE MAP (for lower groundwater zone)** <br> (option InitLisflood)   ||||
| $^1$ average inflow to lower zone | $\frac{mm}{day}$ | lzavin.map      | other fraction  |
| $^1$ average inflow to lower zone (forest) | $\frac{mm}{day}$ | lzavin\_forest.map | forest fraction |
| **INITIAL CONDITION MAPS at defined time steps**[^26] <br> (option *repStateMaps*) ||||
| $^2$ waterdepth | $mm$    | wdepth00.xxx    | whole pixel     |
| $^2$ channel cross-sectional area | $m^2$  | chcro000.xxx    | channel         |
| $^2$ days since last rain variable | $days$   | dslr0000.xxx    | other pixel     |
| $^2$ snow cover zone *A* | $mm$ | scova000.xxx    | snow zone A ($\frac{1}{3}$ pixel) |
| $^2$ snow cover zone *B* | $mm$ | scovb000.xxx    | snow zone B ($\frac{1}{3}$ pixel) |
| $^2$ snow cover zone *C* | $mm$ | scovc000.xxx    | snow zone C ($\frac{1}{3}$ pixel) |
| $^2$ frost index | $\frac{°C}{days}$ | frost000.xxx    | other pixel     |
| $^2$ cumulative interception | $mm$ | cumi0000.xxx    | other pixel     |
| $^2$ soil moisture upper layer | $\frac{mm^3}{mm^3}$ | thtop000.xxx    | other fraction  |
| $^2$ soil moisture lower layer |      | $\frac{mm^3}{mm^3}$thsub000.xxx | other fraction  |
| $^2$ water in lower zone | $mm$ | lz000000.xxx    | other fraction  |
| $^2$ water in upper zone | $mm$ | uz000000.xxx    | other fraction  |
| $^2$ days since last rain variable (forest) | $days$  | dslF0000.xxx    | forest pixel    |
| $^2$ cumulative interception (forest) | $mm$ | cumF0000.xxx    | forest pixel    |
| $^2$ soil moisture upper layer (forest) | $\frac{mm^3}{mm^3}$ | thFt0000.xxx | forest fraction |
| $^2$ soil moisture lower layer (forest) | $\frac{mm^3}{mm^3}$ | thFs0000.xxx    | forest fraction |
| $^2$ water in lower zone (forest) | $mm$ | lzF00000.xxx    | forest fraction |
| $^2$ water in upper zone (forest) | $mm$ | uzF00000.xxx    | forest fraction |
| $^2$ water in depression storage (sealed) | $mm$ | cseal000.xxx    | sealed fraction |

$^1$ Output only if option 'InitLisflood' = 1 (pre-run) \  
$^2$ Output only if option 'InitLisflood' = 0  



***Table:*** *LISFLOOD optional output maps (only 'InitLisflood' = 0)*    

| **Description** | **Option**  | **Units**   | **Settings variable** | **Prefix**  |
|-------------|-------------|-------------|-------------|-------------|
| **DISCHARGE AND WATER LEVEL**     |||||
| discharge   | repDischargeMaps | $\frac{m^3}{s}$ | DischargeMaps | dis         |
| water level | repWaterLevelMaps | $m$ (above channel bottom) | WaterLevelMaps | wl          |
| **METEOROLOGICAL INPUT VARIABLES** |||||
| precipitation | repPrecipitationMaps | $mm$     | PrecipitationMaps | pr          |
| potential reference evapotranspiration| repETRefMaps | $mm$      | ETRefMaps   | et          |
| potential evaporation from soil  | repESRefMaps | $mm$      | ESRefMaps   | es          |
| potential open water evaporation   | repEWRefMaps | $mm$      | EWRefMaps   | ew          |
| average daily temperature | repTavgMaps | $mm$      | TavgMaps    | tav         |
| **STATE VARIABLES** [^30]       |||||
| depth of water on soil surface | repWaterDepthMaps | $mm$      | WaterDepthMaps | wdep        |
| depth of snow cover on soil surface | repSnowCoverMaps | $mm$     | SnowCoverMaps | scov        |
| depth of interception storage | repCumInterceptionMaps | $mm$   | CumInterceptionMaps <br> CumInterceptionForestMaps | cumi <br> <br> cumF       |
| soil moisture content upper layer | repTheta1Maps | $\frac{mm^3}{mm^3}$ | Theta1Maps <br> Theta1ForestMaps | thtop <br> <br> thFt      |
| soil moisture content lower layer | repTheta2Maps | $\frac{mm^3}{mm^3}$ | Theta1Maps <br> Theta1ForestMaps | thsub <br> <br> thFs      |
| storage in upper groundwater zone | repUZMaps   | $mm$    | UZMaps <br> UZForestMaps     | uz <br> <br> uzF        |
| storage in lower groundwater zone | repLZMaps   | $mm$      | LZMaps <br> LZForestMaps     | lz <br> <br> lzF        |
| number of days since last rain  | repDSLRMaps | $days$     | DSLRMaps <br> DSLRForestMaps   | dslr <br> <br> dslF       |
| frost index | repFrostIndexMaps | $\frac{°C}{days}$ | FrostIndexMaps | frost       |
| **RATE VARIABLES** [^31]       |||||
| rain (excluding snow) | repRainMaps | $\frac{mm}{timestep}$ | RainMaps    | rain        |
| snow        | repSnowMaps | $\frac{mm}{timestep}$ | SnowMaps    | snow        |
| snow melt   | repSnowMeltMaps | $\frac{mm}{timestep}$ | SnowMeltMaps | smelt       |
| actual evaporation      | repESActMaps | $\frac{mm}{timestep}$ | ESActMaps   | esact       |
| actual transpiration     | repTaMaps   | $\frac{mm}{timestep}$ | TaMaps      | tact        |
| rainfall interception   | repInterceptionMaps | $\frac{mm}{timestep}$ | InterceptionMaps | int         |
| evaporation of intercepted water | repEWIntMaps | $\frac{mm}{timestep}$ | EWIntMaps   | ewint       |
| leaf drainage       | repLeafDrainageMaps | $\frac{mm}{timestep}$ | LeafDrainageMaps | ldra        |
| infiltration | repInfiltrationMaps | $\frac{mm}{timestep}$ | InfiltrationMaps | inf         |
| preferential (bypass) flow | repPrefFlowMaps | $\frac{mm}{timestep}$ | PrefFlowMaps | pflow       |
| percolation upper to lower soil layer | repPercolationMaps | $\frac{mm}{timestep}$ | PercolationMaps | to2su       |
| percolation lower soil layer to subsoil | repSeepSubToGWMaps | $\frac{mm}{timestep}$ | SeepSubToGWMaps | su2gw       |
| surface runoff | repSurfaceRunoffMaps | $\frac{mm}{timestep}$ | SurfaceRunoffMaps | srun        |
| outflow from upper zone | repUZOutflowMaps | $\frac{mm}{timestep}$ | UZOutflowMaps | quz         |
| outflow from lower zone | repLZOutflowMaps | $\frac{mm}{timestep}$ | LZOutflowMaps | qlz         |
| total runoff      | repTotalRunoffMaps | $\frac{mm}{timestep}$ | TotalRunoffMaps | trun        |
| percolation upper to lower zone | repGwPercUZLZMaps | $\frac{mm}{timestep}$ | GwPercUZLZMaps | uz2lz       |
| loss from lower zone  | repGwLossMaps         | $\frac{mm}{timestep}$ | GwLossMaps  | loss        |


# Output tables (time series)


***Table:*** *LISFLOOD default output tables (time series)*.  

| **Settings variable**     | **File name**   | **Units**       | **Description** |
|-------------------|-----------------|-----------------|--------------------------|
| **RATE VARIABLES AT GAUGES**        ||||
| disTS           | dis.tss         | $\frac{m^3}{s}$ | $^{1,2}$ channel discharge |
| **NUMERICAL CHECKS**               |                 |                 |      |
| WaterMassBalanc eTSS| mbError.tss     | $m^3$          | $^2$ cumulative mass balance error |
| MassBalanceMM\ TSS | mbErrorMm.tss   | $mm$           | $^2$ cumulative mass balance error, expressed as mm water slice (average over catchment) |
| NosupStepsChan  | NosupStepsChannel.tss | \-              | $^2$ number of sup-steps needed for channel routing |
| StepsSoilTS     | steps.tss       | \-              | $^2$ number of sup-steps needed for gravity-based soil moisture routine |

$^1$ Output only if option 'InitLisflood' = 1 (pre-run) \
$^2$ Output only if option 'InitLisflood' = 0      

***Table:*** *LISFLOOD optional output tables (time series; *only 'InitLisflood' = 0).*   

| **Settings variable**     | **File name**       | **Units**       | **Description** |
|-----------------|-------------------|-----------------|--------------------------|
| **STATE VARIABLES AT  SITES <br> (option *repStateSites*)**[^22]        ||||
| WaterDepthTS    | wDepth.tss      | $mm$           | depth of water on soil surface |
| SnowCoverTS     | snowCover.tss   | $mm$          | depth of snow cover on soil surface (pixel-average) |
| CumInterception TS| cumInt.tss      | $mm$          | depth of interception storage|
| Theta1TS        | thTop.tss       | $\frac{mm^3}{mm^3}$ | soil moisture content upper layer |
| Theta2TS        | thSub.tss       | $\frac{mm^3}{mm^3}$ | soil moisture content lower layer |
| UZTS            | uz.tss          | $mm$         | storage in upper groundwater zone |
| LZTS            | lz.tss          | $mm$          | storage in lower groundwater zone |
| DSLRTS          | dslr.tss        | $days$         | number of days since last rain |
| FrostIndexTS    | frost.tss       | $\frac{°C}{days}$ | frost index     |
| RainTS          | rain.tss         | $\frac{mm}{timestep}$ | rain (excluding snow)                  |
| SnowTS          | snow.tss         | $\frac{mm}{timestep}$ | Snow                                   |
| SnowmeltTS      | snowMelt.tss     | $\frac{mm}{timestep}$ | snow melt                              |
| ESActTS         | esAct.tss        | $\frac{mm}{timestep}$ | actual evaporation                     |
| TaTS            | tAct.tss         | $\frac{mm}{timestep}$ | actual transpiration                   |
| InterceptionTS  | interception.tss | $\frac{mm}{timestep}$ | rainfall interception                  |
| EWIntTS         | ewIntAct.tss     | $\frac{mm}{timestep}$ | evaporation of intercepted water       |
| LeafDrainageTS  | leafDrainage.tss | $\frac{mm}{timestep}$ | leaf drainage                          |
| InfiltrationTS  | infiltration.tss | $\frac{mm}{timestep}$ | infiltration                           |
| PrefFlowTS      | prefFlow.tss     | $\frac{mm}{timestep}$ | preferential (bypass) flow             |
| PercolationTS   | dTopToSub.tss    | $\frac{mm}{timestep}$ | percolation upper to lower soil layer  |
| SeepSubToGWTS   | dSubToUz.tss     | $\frac{mm}{timestep}$ | percolation lower soil layer to subsoil|
| SurfaceRunoffTS | surfaceRunoff.tss| $\frac{mm}{timestep}$ | surface runoff                         |
| UZOutflowTS     | qUz.tss          | $\frac{mm}{timestep}$ | outflow from upper zone                |
| LZOutflowTS     | qLz.tss          | $\frac{mm}{timestep}$ | outflow from lower zone                |
| TotalRunoffTS   | totalRunoff.tss  | $\frac{mm}{timestep}$ | total runoff                           |
| GwPercUZLZTS    | percUZLZ.tss     | $\frac{mm}{timestep}$ | percolation from upper to lower zone   |
| GwLossTS        | loss.tss         | $\frac{mm}{timestep}$ | loss from lower zone                   |
| **METEOROLOGICAL INPUT VARIABLES <br> (option *repMeteoUpsGauges*)**  ||||
| PrecipitationAv UpsTS| precipUps.tss   | $\frac{mm}{timestep}$ | precipitation   |
| ETRefAvUpsTS    | etUps.tss       | $\frac{mm}{timestep}$ | potential reference evapotranspiration      |
| ESRefAvUpsTS    | esUps.tss       | $\frac{mm}{timestep}$ | potential evaporation from soil       |
| EWRefAvUpsTS    | ewUps.tss       | $\frac{mm}{timestep}$ | potential open water evaporation |
| TavgAvUpsTS     | tAvgUps.tss     | $°C$            | average daily temperature  |
| **STATE VARIABLES <br> (option *repStateUpsGauges*)**        ||||
| WaterDepthAvUpsTS | wdepthUps.tss   | $mm$           | depth of water on soil surface |
| SnowCoverAvUpsTS | snowCoverUps.tss | $mm$         | depth of snow   |
| CumInterceptionAvUpsTS | cumInterceptionUps.tss | $mm$         | depth of interception storage       |
| Theta1AvUpsTS   | thTopUps.tss    | $\frac{mm^3} {mm^3}$ | soil moisture upper layer  |
| Theta2AvUpsTS   | thSubUps.tss    | $\frac{mm^3} {mm^3}$ | soil moisture lower layer   |
| UZAvUpsTS       | uzUps.tss       | $mm$          | groundwater upper zone  |
| LZAvUpsTS       | lzUps.tss       | $mm$         | groundwater lower zone    |
| DSLRAvUpsTS     | dslrUps.tss     | $days$          | number of days since last rain |
| FrostIndexAvUpsTS | frostUps.tss    | $\frac{°C}{days}$ | frost index     |
| **RATE VARIABLES <br> (option *repRateUpsGauges*)** ||||
| RainAvUpsTS     | rainUps.tss     | $\frac{mm}{timestep}$ | rain (excluding snow)|
| SnowAvUpsTS     | snowUps.tss     | $\frac{mm}{timestep}$ | snow            |
| SnowmeltAvUpsTS | snowMeltUps.tss | $\frac{mm}{timestep}$ | snow melt       |
| ESActAvUpsTS    | esActUps.tss    | $\frac{mm}{timestep}$ | actual evaporation         |
| TaAvUpsTS       | tActUps.tss     | $\frac{mm}{timestep}$ | actual transpiration |
| InterceptionAvUpsTS | interceptionUps.tss  | $\frac{mm}{timestep}$ | rainfall interception |
| EWIntAvUpsTS    | ewIntActUps.tss | $\frac{mm}{timestep}$ | evaporation of intercepted water |
| LeafDrainageAvUpsTS | leafDrainageUps.tss | $\frac{mm}{timestep}$ | leaf drainage   |
| InfiltrationAvUpsTS | infiltrationUps.tss | $\frac{mm}{timestep}$ | infiltration    |
| PrefFlowAvUpsTS | prefFlowUps.tss | $\frac{mm}{timestep}$ | preferential (bypass) flow |
| PercolationAvUpsTS | dTopToSubUps.tss | $\frac{mm}{timestep}$ | percolation upper to lower soil layer    |
| SeepSubToGWAvUpsTS | dSubToUzUps.tss | $\frac{mm}{timestep}$ | percolation lower soil layer to subsoil |
| SurfaceRunoffAvUpsTS | surfaceRunoffUps.tss | $\frac{mm}{timestep}$ | surface runoff  |
| UZOutflowAvUpsTS | qUzUps.tss      | $\frac{mm}{timestep}$ | outflow from upper zone|
| LZOutflowAvUpsTS | qLzUps.tss      | $\frac{mm}{timestep}$ | outflow from lower zone   |
| TotalRunoffAvUpsTS | totalRunoffUps.tss | $\frac{mm}{timestep}$ | total runoff    |
| GwPercUZLZAvUpsTS | percUZLZUps.tss | $\frac{mm}{timestep}$ | percolation upper to lower zone |
| GwLossTS        | lossUps.tss     | $\frac{mm}{timestep}$ | loss from lower zone |
| **WATER LEVEL IN CHANNEL <br> (option *repWaterLevelTs*)** ||||
| WaterLevelTS        | waterLevel.tss     | $m$ (above channel bottom)   | water level in channel |
| **OUTPUT RELATED TO LOWER ZONE INITIALISATION <br> (option *repLZAvInflowSites* and *repLZAvInflowUpsGauges*)** ||||
| LZAvInflowTS        | lzAvIn.tss     | $\frac{mm}{day}$ | average inflow into lower zone |
| LZAvInflowAvUpsTS        | lzAvInUps.tss     | $\frac{mm}{day}$ | average inflow into lower zone |

