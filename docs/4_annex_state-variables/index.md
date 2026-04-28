**Table:** *State variables, required for warm start of model simulations.*

| Key                            | LISFLOOD file name | LISFLOOD variable     | Unit | Description                                                                                       |
|--------------------------------|--------------------|-----------------------| ---- |---------------------------------------------------------------------------------------------------|
| OFDirectState                  | ofdir              | OFM3Direct            | m3   | Water volume on catchment surface for direct fraction                                             |
| OFOtherState                   | ofoth              | OFM3Other             | m3   | Water volume on catchment surface for other fraction                                              |
| OFForestState                  | offor              | OFM3Forest            | m3   | Water volume on catchment surface for forest fraction                                             |
| ChanCrossSectionState          | chcro              | TotalCrossSectionArea | m2   | Total cross-section area of channel                                                               |
| DSLRState                      | dslr               | DSLR[0]               | day  | Reported days since last rain                                                                     |
| DSLRForestState                | dslf               | DSLR[1]               | day  | Reported days since last rain for forest                                                          |
| DSLRIrrigationState            | dsli               | DSLR[2]               | day  | Reported days since last rain irrigation                                                          |
| SnowCoverAState                | scova              | SnowCoverS[0]         | mm   | Reported snow cover in snow zone A                                                                |
| SnowCoverBState                | scovb              | SnowCoverS[1]         | mm   | Reported snow cover in snow zone B                                                                |
| SnowCoverCState                | scovc              | SnowCoverS[2]         | mm   | Reported snow cover in snow zone C                                                                |
| FrostIndexState                | frost              | FrostIndex            | C/day| Reported frost index                                                                              |
| CumInterceptionState           | cum                | CumInterception[0]    | mm   | Reported interception storage                                                                     |
| CumInterceptionForestState     | cumf               | CumInterception[1]    | mm   | Reported interception storage for forest                                                          |
| CumInterceptionIrrigationState | cumi               | CumInterception[2]    | mm   | Reported interception storage for irrigation                                                      |
| CumIntSealedState              | cseal              | CumInterSealed        | mm   | Reported cumulative depressions storage                                                           |
| Theta1State                    | tha                | Theta1a[0]            | -    | Reported volumetric soil water content for superficial soil layer (1a), other fraction [V/V]      |
| Theta1ForestState              | thfa               | Theta1a[1]            | -    | Reported volumetric soil water content for superficial soil layer (1a), forest fraction [V/V]     |
| Theta1IrrigationState          | thia               | Theta1a[2]            | -    | Reported volumetric soil water content for superficial soil layer (1a), irrigation fraction [V/V] |
| Theta2State                    | thb                | Theta1b[0]            | -    | Reported volumetric soil water content for upper soil layer (1b), other fraction [V/V]            |
| Theta2ForestState              | thfb               | Theta1b[1]            | -    | Reported volumetric soil water content for upper soil layer (1b), forest fraction [V/V]           |
| Theta2IrrigationState          | thib               | Theta1b[2]            | -    | Reported volumetric soil water content upper soil layer (1b), irrigation fraction [V/V]           |
| Theta3State                    | thc                | Theta2[0]             | -    | Reported volumetric soil water content for lower soil layer (2), other fraction [V/V]             |
| Theta3ForestState              | thfc               | Theta2[1]             | -    | Reported volumetric soil water content for lower soil layer (2), forest   fraction [V/V]          |
| Theta3IrrigationState          | thic               | Theta2[2]             | -    | Reported volumetric soil water content for for lower soil layer (2), irrigation  fraction [V/V]   |
| UZState                        | uz                 | UZ[0]                 | mm   | Reported storage in upper groundwater zone, other fraction                                        |
| UZForestState                  | uzf                | UZ[1]                 | mm   | Reported storage in upper groundwater zone, forest fraction                                       |
| UZIrrigationState              | uzi                | UZ[2]                 | mm   | Reported storage in upper groundwater zone, irrigation fraction                                   |
| LZState                        | lz                 | LZ                    | mm   | Reported storage in lower groundwater zone                                                        |
| ChanQState                     | chanq              | ChanQ                 | m3/s | Reported istantaneous discarge at end of the model time step                                      |
| ChanQAvgDtState *L             | chanqavgdt         | ChanQAvgDt            | m3/s | Reported average discarge for the last routing sub-step                                           |
| LakeLevelState *L              | lakeh              | LakeLevel             | m    | Output map(s) with lake level                                                                     |
| LakePrevInflowState *L         | lakeprevinq        | LakeInflowOld         | m3/s | Output map with lake average inflow at previous routing sub-step (ChanQ(t-1))                     |
| LakePrevOutflowState *L        | lakeprevoutq       | LakeOutflow           | m3/s | Output map with lake average outflow at previous routing sub-step (ChanQ(t-1))                    |
| ReservoirFillState *R          | rsfil              | ReservoirFill         | -    | Output map(s) with Reservoir Filling [V/V]                                                        |
| CrossSection2State *SR         | ch2cr              | CrossSection2Area     | m2   | Cross section area for split routing                                                              |
| ChSideState *SR                | chside             | Sideflow1Chan         | m2/s | Sideflow to channel  for 1st line   of routing                                                    |
| PrevCmMCTState *MCT            | prevcm             | PrevCmMCT             | -    | Courant number at previous step for MCT routing                                                   |
| PrevDmMCTState *MCT            | prevdm             | PrevDmMCT             | -    | Reynolds number at previous step for MCT routing                                                  |

*L = this state variable is required when lakes are included in the modelling domain
*R = this state variable is required when reservoirs are included in the modelling domain
*SR = this state variable is required when using the split routing module
*MCT = this state variable is required when using diffusive routing (MCT)