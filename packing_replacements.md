# Find-and-Replace Guide: scale_factor / add_offset Values

Replace `scale_factor=1, add_offset=0` with the correct values below.
Use your editor's find-and-replace on each variable name to locate it.

**Important:** For State/End entries, REMOVE scale_factor and add_offset entirely
(let them default to None). They should never be packed.

---

## Variables to REMOVE packing from (State/End maps — set to None)

These have `scale_factor=1, add_offset=0` but should NOT be packed.
Remove the `, scale_factor=1, add_offset=0` from these entries entirely:

- SnowCoverAEnd, SnowCoverAState
- SnowCoverBEnd, SnowCoverBState  
- SnowCoverCEnd, SnowCoverCState
- Theta1End, Theta1State, Theta1ForestState, Theta1IrrigationState
- Theta2ForestState, Theta2IrrigationState, Theta2State
- Theta3ForestState, Theta3IrrigationState, Theta3State
- UZForestState, UZIrrigationState, UZState
- WaterDepthState
- SeepTopToSubBAverageOtherMap (end=['InitLisflood'] — this is a prerun end map)
- SeepTopToSubBAverageForestMap (end=['InitLisflood'])
- SeepTopToSubBAverageIrrigationMap (end=['InitLisflood'])

---

## Variables to UPDATE with proper values

Format: `VariableName` → `scale_factor=X, add_offset=Y`
Design range and precision shown for reference.

### Discharge (m3/s) — range 0 to 400,000
- `DischargeMaps` → `scale_factor=6.104, add_offset=200000.0`

### Direct Runoff (mm) — range 0 to 400
- `DirectRunoffMaps` → `scale_factor=0.006104, add_offset=200.0`

### Evaporation (mm/day) — range 0 to 20
- `ESActMaps` → `scale_factor=3.052e-4, add_offset=10.0`
- `ESRefMapsOut` → `scale_factor=3.052e-4, add_offset=10.0`

### ET (mm/day) — range -10 to 1000
- `ETActMaps` → `scale_factor=0.01541, add_offset=495.0`
- `ETActBudykoMaps` → `scale_factor=0.01541, add_offset=495.0`
- `ETRefMapsOut` → `scale_factor=3.052e-4, add_offset=10.0`

### Interception/Transpiration (mm/day) — range 0 to 15
- `EWIntForestMaps` → `scale_factor=2.289e-4, add_offset=7.5`
- `EWIntMaps` → `scale_factor=2.289e-4, add_offset=7.5`
- `EWRefMapsOut` → `scale_factor=3.052e-4, add_offset=10.0`
- `EWater` → `scale_factor=3.052e-4, add_offset=10.0`
- `InterceptionForestMaps` → `scale_factor=2.289e-4, add_offset=7.5`
- `InterceptionMaps` → `scale_factor=2.289e-4, add_offset=7.5`

### Fast Runoff / Preferential Flow (mm) — range 0 to 400
- `FastRunoffMaps` → `scale_factor=0.006104, add_offset=200.0`

### GW Percolation UZ to LZ (mm) — range 0 to 3
- `GwPercUZLZForestMaps` → `scale_factor=4.578e-5, add_offset=1.5`
- `GwPercUZLZIrrigationMaps` → `scale_factor=4.578e-5, add_offset=1.5`
- `GwPercUZLZOtherMaps` → `scale_factor=4.578e-5, add_offset=1.5`
- `GwPercUZLZMaps` → `scale_factor=4.578e-5, add_offset=1.5`

### Infiltration (mm) — range 0 to 500
- `InfiltrationForestMaps` → `scale_factor=0.007630, add_offset=250.0`
- `InfiltrationMaps` → `scale_factor=0.007630, add_offset=250.0`

### Seep to GW (mm) — range 0 to 60
- `SeepSubToGWMaps` → `scale_factor=9.156e-4, add_offset=30.0`

### Snow (mm) — range 0 to 200
- `SnowMaps` → `scale_factor=0.003052, add_offset=100.0`

### Snow Cover (mm) — range 0 to 10000
- `SnowCoverMaps` → `scale_factor=0.15260, add_offset=5000.0`

### Snow Melt (mm) — range 0 to 250
- `SnowMeltMaps` → `scale_factor=0.003815, add_offset=125.0`

### Surface Runoff (mm) — range 0 to 500
- `SurfaceRunoffMaps` → `scale_factor=0.007630, add_offset=250.0`

### Transpiration (mm/day) — range -10 to 15
- `TaOtherMaps` → `scale_factor=3.815e-4, add_offset=2.5`
- `TaForestMaps` → `scale_factor=3.815e-4, add_offset=2.5`
- `TaIrrigationMaps` → `scale_factor=3.815e-4, add_offset=2.5`
- `TaMaps` → `scale_factor=3.815e-4, add_offset=2.5`

### Theta (soil moisture fraction) — range 0 to 1
- `Theta1Maps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta1ForestMaps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta1IrrigationMaps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta2Maps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta2ForestMaps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta2IrrigationMaps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta3Maps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta3ForestMaps` → `scale_factor=1.526e-5, add_offset=0.5`
- `Theta3IrrigationMaps` → `scale_factor=1.526e-5, add_offset=0.5`

### Total Runoff (mm) — range 0 to 500
- `TotalRunoffMaps` → `scale_factor=0.007630, add_offset=250.0`
- `TotalToChanMaps` → `scale_factor=0.007630, add_offset=250.0`

### Transmission Loss (mm) — range 0 to 600
- `TransLossMaps` → `scale_factor=0.009156, add_offset=300.0`

### UZ (mm) — range 0 to 3500
- `UZForestMaps` → `scale_factor=0.05341, add_offset=1750.0`
- `UZIrrigationMaps` → `scale_factor=0.05341, add_offset=1750.0`
- `UZMaps` → `scale_factor=0.05341, add_offset=1750.0`

### UZ Outflow (mm) — range 0 to 300
- `UZOutflowForestMaps` → `scale_factor=0.004578, add_offset=150.0`
- `UZOutflowIrrigationMaps` → `scale_factor=0.004578, add_offset=150.0`
- `UZOutflowOtherMaps` → `scale_factor=0.004578, add_offset=150.0`
- `UZOutflowMaps` → `scale_factor=0.004578, add_offset=150.0`

### Water Depth (mm) — range 0 to 250
- `WaterDepthMaps` → `scale_factor=0.003815, add_offset=125.0`

### Total Water Storage (mm) — range -5000 to 35,000,000
- `TotalWaterStorageMaps` → **DO NOT PACK** (range too large for int16). Remove scale_factor/add_offset.

