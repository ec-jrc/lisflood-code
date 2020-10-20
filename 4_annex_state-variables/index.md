**Table:** *State variables.*

| Key                            | LISFLOOD file name | LISFLOOD variable     | Unit | Lxop    | Description                                                  |
| ------------------------------ | ------------------ | --------------------- | ---- | ------- | ------------------------------------------------------------ |
| OFDirectState                  | ofdir              | OFM3Direct            | m3   | ofdir   | Water volume on catchment   surface for direct fraction [m3] |
| OFOtherState                   | ofoth              | OFM3Other             | m3   | ofoth   | Water volume on catchment   surface for other fraction [m3]  |
| OFForestState                  | offor              | OFM3Forest            | m3   | offor   | Water volume on catchment   surface for forest fraction [m3] |
| ChanCrossSectionState          | chcro              | TotalCrossSectionArea | m    | chcross | Total cross-section area of channel                          |
| DSLRState                      | dslr               | DSLR[0]               | -    | dslr    | Reported days since last rain                                |
| DSLRForestState                | dslf               | DSLR[1]               | -    | dslf    | Reported days since last rain for forest                     |
| DSLRIrrigationState            | dsli               | DSLR[2]               | -    | dsli    | Reported days since last rain irrigation                     |
| SnowCoverAState                | scova              | SnowCoverS[0]         | mm   | scova   | Reported snow cover in snow zone A [mm]                      |
| SnowCoverBState                | scovb              | SnowCoverS[1]         | mm   | scovb   | Reported snow cover in snow zone B [mm]                      |
| SnowCoverCState                | scovc              | SnowCoverS[2]         | mm   | scovc   | Reported snow cover in snow zone C [mm]                      |
| FrostIndexState                | frost              | FrostIndex            | -    | frost   | Reported frost index                                         |
| CumInterceptionState           | cum                | CumInterception[0]    | mm   | cumint  | Reported interception storage                                |
| CumInterceptionForestState     | cumf               | CumInterception[1]    | mm   | cumf    | Reported interception storage for forest                     |
| CumInterceptionIrrigationState | cumi               | CumInterception[2]    | mm   | cumi    | Reported interception storage for irrigation                 |
| Theta1State                    | tha                | Theta1a[0]            | -    | thtop   | Reported volumetric soil moisture content for top soil layer 1a [V/V] |
| Theta1ForestState              | thfa               | Theta1a[1]            | -    | thfa    | Reported volumetric soil moisture content for top soil layer 1a forest   fraction [V/V] |
| Theta1IrrigationState          | thia               | Theta1a[2]            | -    | thia    | Reported volumetric soil moisture content for top soil layer 1a irrigation   fraction [V/V] |
| Theta2State                    | thb                | Theta1b[0]            | -    | thsub   | Reported volumetric soil moisture content for  soil layer 1b [V/V] |
| Theta2ForestState              | thfb               | Theta1b[1]            | -    | thfb    | Reported volumetric soil moisture content for  soil layer 1b forest fraction [V/V] |
| Theta2IrrigationState          | thib               | Theta1b[2]            | -    | thib    | Reported volumetric soil moisture content for  soil layer 1b irrigation fraction [V/V] |
| Theta3State                    | thc                | Theta2[0]             | -    | thc     | Reported volumetric soil moisture content for soil layer 2 [V/V] |
| Theta3ForestState              | thfc               | Theta2[1]             | -    | thfc    | Reported volumetric soil moisture content for soil layer 2 forest   fraction [V/V] |
| Theta3IrrigationState          | thic               | Theta2[2]             | -    | thic    | Reported volumetric soil moisture content for soil layer 2   irrigation  fraction [V/V] |
| UZState                        | uz                 | UZ[0]                 | mm   | uz      | Reported storage in upper groundwater zone response box [mm] |
| UZForestState                  | uzf                | UZ[1]                 | mm   | uzf     | Reported storage in upper groundwater zone response box for forest [mm] |
| UZIrrigationState              | uzi                | UZ[2]                 | mm   | uzi     | Reported storage in upper groundwater zone response box for irrigation   [mm] |
| LZState                        | lz                 | LZ                    | mm   | lz      | Reported storage in lower response box [mm]                  |
| CumIntSealedState              | cseal              | CumInterSealed        | mm   | cseal   | Reported cumulative depressions storage [mm]                 |
| DischargeMaps                  | dis                | ChanQAvg              | m3/s | dis     | Reported discharge [cu m/s] (average over the timesteps)(not used for   warm start) |
| ChanQState                     | chanq              | ChanQ                 | m3/s | chanq   | Reported istantaneous discarge at end of time step           |
| LakeLevelState                 | lakeh              | LakeLevel             | m    | lakh    | Output map(s) with lake level [m]                            |
| ReservoirFillState             | rsfil              | ReservoirFill         | -    | rsfil   | Output map(s) with Reservoir Filling [V/V]                   |
| CrossSection2State             | ch2cr              | CrossSection2Area     | m    | ch2cr   | Cross section area for split routing [m]                     |
| ChSideState                    | chside             | Sideflow1Chan         | m    | chside  | Sideflow to channel  for 1st line   of routing [m]           |
