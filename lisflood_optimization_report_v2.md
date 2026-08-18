# LISFLOOD Optimization Report v2

## Executive Summary

This report identifies concrete opportunities to reduce wall-clock execution time and storage requirements across the LISFLOOD hydrological model codebase. It supersedes the earlier I/O-focused optimization report by covering the full computational pipeline including the newly added Muskingum-Cunge-Todini (MCT) routing module.

Key findings:

1. **MCT Routing Inner Loop** — The `mct_routing` kernel uses `prange` over pixels within each topological order, but orders are processed serially. The Newton-Raphson solver in `MCTRouting_single` (called twice per pixel) dominates runtime for MCT-enabled runs.
2. **Kinematic Wave Parallel Routing** — Already well-optimized with Numba `@njit(parallel=True)`, but the `numexpr` constant-term evaluation before calling the Numba kernel adds Python overhead every sub-step.
3. **Redundant Array Copies in Routing Loop** — Up to 10+ full-domain `.copy()` calls per routing sub-step when MCT + mass-balance reporting are active.
4. **I/O: Output Data Type** — Default `float64` output is still the factory setting; switching to `float32` halves output storage with no impact on results.
5. **I/O: NetCDF Chunk Size** — Time-dimension chunk of 1 limits compression ratio and read-back performance.
6. **Numba JIT Cold-Start** — First call to each `@njit` function triggers compilation; `cache=True` is already set but AOT pre-compilation could eliminate startup cost entirely.
7. **Memory: `compressArray` forces float64** — All compressed arrays are cast to `float64` regardless of input dtype.


---

## Part A — Runtime Performance

---

### A1. MCT Routing: Serial Order Loop with Parallel Inner Loop

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/mct.py` |
| **Function** | `mct_routing()` (lines ~113-175) |
| **Impact** | **HIGH** |

**Why it is a bottleneck:**
The MCT routing kernel is decorated `@njit(parallel=True)` but only the inner `prange(first, last)` loop over pixels within a single topological order is parallelised. The outer `for order in range(num_orders)` loop is inherently serial (data dependency: downstream pixels need upstream results). For domains with many orders but few pixels per order (long river stems), most iterations run with minimal parallelism.

Inside the inner loop, `MCTRouting_single` is called per pixel. It contains:
- A Newton-Raphson iterative solver (`hoq`) with up to 1000 iterations per call
- Two full iterations of the MCT parameter calibration (`for i in range(2)`)
- Multiple calls to `qoh` (Manning-based Q-h relationships)

For EFAS (~7 million pixels, ~5000 MCT pixels, ~200 topological orders), the MCT kernel can account for 30-50% of the routing sub-step time.

**Recommendations:**

1. **Reduce Newton-Raphson iterations in `hoq`**: The convergence tolerance is `1e-6` and max iterations is 1000. Profile to check actual average iteration count. If typically < 20, the overhead is acceptable. If convergence is slow for certain geometries, consider providing a better initial guess from the previous timestep's water depth (store `y_prev` as state).

2. **Vectorise `MCTRouting_single` for batches**: Instead of calling a scalar function per pixel inside `prange`, restructure to pass arrays of pixel data for each order-batch and process them with vectorised NumPy/Numba array operations. This would enable SIMD and reduce function-call overhead.

3. **Pre-compute static derived quantities**: `np.arctan(1 / ChanSdXdY[kinpix])` is computed every timestep for every pixel. Store `ANalv` as a pre-computed array in `MCTWave.__init__`.

4. **Consider adaptive sub-stepping**: When Courant number < 0.5 for most pixels, the MCT solution is over-resolved. Allow the routing module to skip MCT computation for pixels where flow conditions have not materially changed (delta-Q threshold).


---

### A2. MCT Routing: Redundant `arctan` Computation Per Pixel Per Timestep

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/mct.py` |
| **Function** | `mct_routing()`, inner loop body |
| **Impact** | **MEDIUM** |

**Current code (inside prange loop):**
```python
ANalv = np.arctan(1 / ChanSdXdY[kinpix])
```

**Why it matters:**
`arctan` is a transcendental function computed per pixel, per routing sub-step, per model timestep. For EFAS with 4 routing sub-steps and 5000 MCT pixels, this is 20000 `arctan` calls per model timestep — all with static input. The result never changes.

**Recommendation:**
Pre-compute `ANalv` once during `MCTWave.__init__()` and pass it as an array to `mct_routing`:

```python
# In MCTWave.__init__:
self.ANalv = np.arctan(1.0 / ChanSdXdY)

# In mct_routing signature: add ANalv parameter
# In the inner loop: replace np.arctan(...) with ANalv[kinpix]
```

**Estimated saving:** ~2-5% of MCT kernel time (removes transcendental from hot loop).


---

### A3. Kinematic Wave: `numexpr` Overhead Before Numba Kernel

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/kinematic_wave_parallel.py` |
| **Function** | `kinematicWave.kinematicWaveRouting()` |
| **Impact** | **MEDIUM** |

**Current code:**
```python
lateral_inflow = nx.evaluate("q * dx", local_dict={"q": specific_lateral_inflow, "dx": self.space_delta})
constant = nx.evaluate("a_dx_div_dt * Qold ** b + lateral_inflow", local_dict={...})
```

**Why it matters:**
These `numexpr.evaluate` calls are executed every routing sub-step (typically 2-8 times per model timestep). Each call:
- Creates temporary arrays (full domain size)
- Involves Python-level dict construction and string parsing
- Runs a multi-threaded expression evaluator that competes with Numba's own thread pool

For the kinematic routing (which applies to ALL channel pixels including those later overwritten by MCT), this adds measurable Python overhead on every sub-step.

**Recommendation:**
Move the constant-term computation into the Numba `kinematicRouting` kernel itself. The expressions are simple element-wise operations that Numba can fuse into the main loop without allocating intermediates:

```python
# Inside kinematicRouting (already @njit parallel):
# Replace 'constant' parameter with raw inputs
# Compute constant[pix] = a_dx_div_dt[pix] * discharge[pix]**beta + lateral_inflow[pix]
# directly at point of use
```

Alternatively, replace `numexpr` with a small `@njit` helper that computes `constant` in-place:

```python
@njit(parallel=True, cache=True)
def compute_constant(constant, a_dx_div_dt, discharge, beta, lateral_inflow, space_delta, specific_lateral_inflow):
    for pix in prange(constant.size):
        constant[pix] = a_dx_div_dt[pix] * discharge[pix]**beta + specific_lateral_inflow[pix] * space_delta[pix]
```

**Estimated saving:** 5-10% of kinematic routing time (eliminates temporary array allocations and Python-level overhead per sub-step).


---

### A4. Routing Loop: Excessive `.copy()` Calls Per Sub-Step

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/routing.py` |
| **Function** | `routing.dynamic()` |
| **Impact** | **MEDIUM** |

**Current code pattern (inside the `NoRoutSteps` loop):**
```python
SideflowChanM3 = self.var.ToChanM3RunoffDt.copy()
ChanQ_0 = self.var.ChanQ.copy()
ChanM3_0 = self.var.ChanM3.copy()
ChanQ = self.var.ChanQKin.copy()
ChanM3 = self.var.ChanM3Kin.copy()
ChanQAvgDt = self.var.ChanQKinAvgDt.copy()
ChanQAvgDt_old = self.var.ChanQAvgDt.copy()
# + additional copies inside repMBTs block
```

**Why it matters:**
Each `.copy()` allocates a new array of size `num_channel_pixels` (e.g. ~1.8M for EFAS). With MCT + mass-balance reporting active, there are ~10-12 full-domain copies per sub-step. With 4 sub-steps, that is ~40-48 array allocations per model timestep — pure memory allocation + memcpy overhead.

**Recommendation:**
1. Pre-allocate scratch buffers once in `routing.initial()` and reuse them:
```python
# In initial():
self._buf_ChanQ_0 = np.empty_like(self.var.ChanQ)
self._buf_ChanM3_0 = np.empty_like(self.var.ChanM3)

# In dynamic():
np.copyto(self._buf_ChanQ_0, self.var.ChanQ)  # reuse buffer, no allocation
```

2. For `SideflowChanM3`: it starts from `ToChanM3RunoffDt` and then has values added/subtracted. Use an in-place pattern:
```python
SideflowChanM3 = self._buf_sideflow
np.copyto(SideflowChanM3, self.var.ToChanM3RunoffDt)
if option['openwaterevapo']:
    SideflowChanM3 -= self.var.EvaAddM3Dt
# ...
```

3. For the `repMBTs` block: many `.copy()` calls exist solely to avoid modifying the original. Use indexing with `np.where` or masked assignment instead.

**Estimated saving:** 3-8% of total routing time (reduces GC pressure and memcpy for large domains).


---

### A5. Numba JIT Cold-Start Compilation Overhead

| Attribute | Detail |
|-----------|--------|
| **Files** | `mct.py`, `kinematic_wave_parallel_tools.py`, `soilloop.py` |
| **Functions** | All `@njit` decorated functions |
| **Impact** | **MEDIUM** (one-time cost, significant for short runs / calibration) |

**Why it matters:**
Although `cache=True` is set on all Numba-compiled functions, the cache is invalidated whenever:
- The source file changes (even a comment)
- Numba or NumPy is upgraded
- The function signature changes due to different input dtypes

During calibration workflows (1000s of short runs), the first run in each new environment pays 10-30 seconds of JIT compilation. For the MCT module alone, there are 6 `@njit` functions.

**Recommendations:**

1. **Ahead-of-Time (AOT) compilation**: Use `numba.pycc` to pre-compile the performance-critical kernels into a shared library. This eliminates JIT overhead entirely:
```python
from numba.pycc import CC
cc = CC('lisflood_routing_compiled')

@cc.export('mct_routing', '...')
def mct_routing(...): ...

cc.compile()
```

2. **Warm-up script**: Provide a lightweight `warmup_numba.py` that imports all JIT functions and calls them once with tiny dummy arrays. Run this as part of container/environment setup.

3. **Pin Numba + NumPy versions** in Docker/conda environments to avoid cache invalidation across runs.

**Estimated saving:** 10-30 seconds per cold start; near-zero for warm cache.


---

### A6. Surface Routing: Three Separate Kinematic Wave Calls

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/surface_routing.py` |
| **Function** | `surface_routing.dynamic()` |
| **Impact** | **MEDIUM** |

**Current code:**
```python
self.direct_surface_router.kinematicWaveRouting(self.var.OFQDirectAvg, self.var.OFQDirect, SideflowDirect)
self.other_surface_router.kinematicWaveRouting(self.var.OFQOtherAvg, self.var.OFQOther, SideflowOther)
self.forest_surface_router.kinematicWaveRouting(self.var.OFQForestAvg, self.var.OFQForest, SideflowForest)
```

**Why it matters:**
Three independent kinematic wave routing calls are made sequentially, each with its own Numba kernel invocation. Each call processes the full overland-flow pixel domain. Since these three calls are independent (different land-use fractions with no inter-dependency), they could be batched or run concurrently.

**Recommendations:**

1. **Batch into a single kernel call**: Modify the kinematic routing kernel to accept a "batch" dimension (3 land-use types). Process all three in a single Numba `prange` call, tripling the available parallelism per order:
```python
# Single call handles all 3 land-use fractions
kinematicRoutingBatched(discharge_avg_batch, discharge_batch, lateral_inflow_batch, ...)
```

2. **Alternatively, use Python threading**: Since the three calls release the GIL (Numba `nogil=True` is implicit in `parallel=True`), they can be dispatched to a `ThreadPoolExecutor` with 3 workers. Each call then runs on its own Numba thread pool subset.

**Estimated saving:** 10-25% of surface routing time (better core utilisation).


---

### A7. Soil Loop: Numba Thread Contention with Numexpr

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/soilloop.py` |
| **Functions** | `soilColumnsWaterBalance`, `interception_water_balance` |
| **Impact** | **LOW-MEDIUM** |

**Why it matters:**
The soil module uses both `numexpr` (via `nx.evaluate`) and Numba `@njit(parallel=True)` with `prange`. Both libraries spawn their own thread pools:
- Numba uses the TBB or OpenMP backend
- numexpr uses its own thread pool (default: number of cores)

When both are active in the same process, they compete for CPU cores. This over-subscription can cause context-switching overhead, especially on HPC nodes with many cores.

**Recommendations:**

1. **Limit numexpr threads**: Set `numexpr.set_num_threads(1)` when Numba parallel functions are the primary workload. Or coordinate thread counts: `NUMEXPR_MAX_THREADS=4` and `NUMBA_NUM_THREADS=N-4`.

2. **Replace remaining numexpr calls with Numba**: The soil module already has extensive Numba coverage. The few remaining `nx.evaluate` calls (in `kinematic_wave_parallel.py`) can be absorbed into Numba kernels, eliminating the second thread pool entirely.

3. **Set `NUMBA_THREADING_LAYER=tbb`** explicitly in the environment to ensure deterministic thread management.

**Estimated saving:** 2-5% overall on many-core systems (16+ cores).


---

### A8. I/O: Synchronous Chunk Loading in XarrayChunked

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/netcdf.py` |
| **Function** | `XarrayChunked.load_next_chunk()` and `XarrayChunked.__getitem__()` |
| **Impact** | **LOW-MEDIUM** |

**Current code:**
```python
def load_next_chunk(self):
    self.ichunk += 1
    begin = self.chunk_indexes[self.ichunk]
    end = self.chunk_indexes[self.ichunk+1]
    chunk = self.dataset.isel(time=range(begin, end))
    self.dataset_chunk = chunk.load()  # blocks until data is in memory
```

**Why it matters:**
When a new temporal chunk boundary is crossed, the model blocks while xarray loads the next chunk from disk. For 5 forcing variables (Precip, Tavg, ET0, ES0, E0), this happens synchronously in `readmeteo.dynamic()`. Each chunk load involves NetCDF decompression (zlib) which is CPU-bound.

**Recommendations:**

1. **Prefetch next chunk asynchronously**: Use a background thread to load the next chunk before it is needed:
```python
import threading

def load_next_chunk(self):
    self.ichunk += 1
    begin = self.chunk_indexes[self.ichunk]
    end = self.chunk_indexes[self.ichunk+1]
    chunk = self.dataset.isel(time=range(begin, end))
    self.dataset_chunk = chunk.load()

def prefetch_next_chunk(self):
    if self.ichunk + 1 < len(self.chunk_indexes) - 1:
        self._prefetch_thread = threading.Thread(target=self._prefetch)
        self._prefetch_thread.start()
```

2. **Increase chunk size**: The setting `NetCDFTimeChunks` controls chunk size. For daily forcing over a year, set to 365 (load entire year at once). Memory cost is modest: 5 variables * 1.8M pixels * 365 days * 4 bytes = ~13 GB for float32 EFAS forcing loaded fully in memory.

3. **Use `MapsCaching=True`** for forcing data when memory permits — loads the entire time series at initialization.

**Estimated saving:** 1-5% for chunked reads; up to 10% if chunk boundaries align with expensive computation.


---

### A9. Output Writing: Per-Timestep NetCDF Writes

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/output.py` |
| **Functions** | `NetcdfStepsWriter.stage()`, `NetcdfStepsWriter.write()` |
| **Impact** | **LOW-MEDIUM** |

**Current behaviour:**
The `OutputMapsChunks` setting (default 1) controls how many timesteps are buffered before writing. With default=1, every reporting timestep triggers:
1. `uncompress_array()` — reconstruct 2D map from compressed 1D array
2. File open (or keep-open via `iterOpenNetcdf`)
3. Single-slice write to NetCDF variable
4. File close (if chunk boundary)

**Why it matters:**
For runs reporting every timestep (e.g. hourly discharge maps for a year = 8760 writes), the overhead of repeated file I/O becomes significant. Each write involves:
- Python-level overhead of netCDF4 library calls
- OS-level file metadata updates
- zlib compression of each 2D slice

**Recommendations:**

1. **Increase `OutputMapsChunks`**: Set to 30-365 depending on output frequency. This buffers multiple timesteps in memory and writes them in a single batch, improving compression ratio and reducing file I/O overhead.

2. **Use the existing `OutputMapsFactoryThreads` class**: The codebase already contains an async-write implementation using `ThreadPool`. It is documented as "NOT FULLY TESTED" but the approach is sound. Validate and enable it as an option:
```xml
<textvar name="AsyncOutputWriting" value="True"/>
```

3. **Batch `uncompress_array` calls**: When writing multiple output variables at the same timestep, the decompression mask operation is repeated for each variable. Cache the mask indexing.

**Estimated saving:** 5-15% for I/O-heavy configurations (many output maps, frequent reporting).


---

### A10. Dynamic Loop: Python-Level Overhead Per Timestep

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/Lisflood_dynamic.py` |
| **Function** | `LisfloodModel_dyn.dynamic()` |
| **Impact** | **LOW** |

**Why it matters:**
Each model timestep involves:
- `datetime.timedelta` computation and `strftime` formatting
- Multiple `if option[...]` checks (dict lookups)
- `sys.stdout.write` and `sys.stdout.flush` for progress reporting

For sub-hourly simulations (e.g. 15-minute timesteps over multiple years), there are 100K+ timesteps. Python-level overhead accumulates.

**Recommendations:**

1. **Cache option flags as local booleans** at the start of `dynamic()`:
```python
opt_MCT = option['MCTRouting']
opt_split = option['SplitRouting']
opt_repMBTs = option['repMBTs']
# use local variables in if-statements
```

2. **Reduce progress output frequency**: Print progress every N steps rather than every step:
```python
if not flags['quiet'] and i % 100 == 0:
    sys.stdout.write(...)
```

3. **Avoid `uuid.uuid4()` on first step**: The CDFFlags initialization creates a UUID on timestep 1. This is a system call that can be slow on some platforms. Move to `initial()`.

**Estimated saving:** 1-2% for very long simulations with many timesteps.


---

### A11. MCT Routing: Calibration Points Check Inside Hot Loop

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/mct.py` |
| **Function** | `mct_routing()`, inner loop |
| **Impact** | **LOW-MEDIUM** |

**Current code:**
```python
for ups_ix in range(num_upstream_pixels[kinpix]):
    ups_pix = upstream_pixels[ups_ix]
    if np.any(CalibPointsIds == ups_pix):
        ql += ChanQAvgDt[ups_pix]
    else:
        q00 += ChanQ_0[ups_pix]
        q0m += ChanQAvgDt[ups_pix]
        q01 += ChanQ[ups_pix]
```

**Why it matters:**
`np.any(CalibPointsIds == ups_pix)` performs a linear scan of the `CalibPointsIds` array for every upstream pixel of every MCT pixel, on every routing sub-step. If there are K calibration points and U upstream connections per pixel, this is O(K * U * num_MCT_pixels * num_substeps) comparisons.

For EFAS with ~50 calibration points and 5000 MCT pixels, this check dominates the inner loop when K is non-trivial.

**Recommendation:**
Replace the linear scan with a pre-computed boolean lookup array:
```python
# In MCTWave.__init__:
is_calib_point = np.zeros(num_all_pixels, dtype=np.bool_)
is_calib_point[CalibPointsIds] = True

# In mct_routing inner loop:
if is_calib_point[ups_pix]:
    ...
```

This changes the check from O(K) to O(1) per upstream pixel.

**Estimated saving:** 5-15% of MCT kernel time when calibration points are active.


---

### A12. Water Balance Module: Repeated `np.bincount` + `np.take` Pattern

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/waterbalance.py` |
| **Function** | `waterbalance.dynamic()` |
| **Impact** | **LOW** |

**Current code pattern (repeated ~10 times):**
```python
WaterIn += np.take(np.bincount(self.var.Catchments, weights=some_array), self.var.Catchments)
```

**Why it matters:**
Each `np.bincount(..., weights=...)` creates a temporary array of size `max(Catchments)+1`, then `np.take` expands it back to full domain size. With 10+ such calls per timestep, this creates substantial temporary memory allocation and cache pressure.

**Recommendations:**

1. **Accumulate weights first, then do a single bincount**: Instead of calling bincount separately for each variable, sum the weighted arrays first:
```python
total_weights = self.var.TotalPrecipitationWB * self.var.MMtoM3
if option['inflow']:
    total_weights += self.var.sumInWB
WaterIn = np.take(np.bincount(self.var.Catchments, weights=total_weights), self.var.Catchments)
```

2. **Pre-allocate the bincount result buffer**: Reuse the same output array across calls.

3. **Consider skipping mass balance for production runs**: The `repMBTs` option enables extensive per-catchment accounting. For operational forecasting (where mass balance is not the focus), disabling this saves all associated computation.

**Estimated saving:** 1-3% of total timestep time.


---

## Part B — Storage & Memory Optimization

---

### B1. Output Data Type: Default float64

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisfloodSettings_reference.xml` (line ~206) |
| **Setting** | `OutputMapsDataType` |
| **Impact** | **HIGH** (50% output storage reduction) |

**Current default:**
```xml
<textvar name="OutputMapsDataType" value="float64"/>
```

**Why it matters:**
All output NetCDF maps are written as float64 (8 bytes per value). For typical hydrological variables (discharge 0-100000 m³/s, soil moisture 0-1, temperature -50 to 50°C), float32 provides ~7 significant digits — more than sufficient.

For an EFAS daily discharge output: 1.8M pixels * 8 bytes * 365 days = ~4.8 GB/year in float64 vs 2.4 GB/year in float32.

**Recommendation:**
Change the default to `float32`:
```xml
<textvar name="OutputMapsDataType" value="float32"/>
```

**Risk:** Very low. Float32 precision (7 significant digits) exceeds the physical accuracy of any hydrological variable LISFLOOD produces. No model results are affected — this is output-only.

**Estimated saving:** 50% reduction in all output map file sizes.


---

### B2. NetCDF Time Chunk Size

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/netcdf.py` (line ~572) |
| **Function** | `write_netcdf_header()` |
| **Impact** | **MEDIUM** (10-30% better compression) |

**Current code:**
```python
value = nf1.createVariable(var_name, dtype, ('time', dim_lat_y, dim_lon_x),
                           zlib=True, fill_value=-9999, chunksizes=(1, nrow, ncol))
```

**Why it matters:**
A time-chunk of 1 means each timestep is compressed independently. Hydrological fields exhibit strong temporal autocorrelation — consecutive timesteps are similar. Compressing multiple timesteps together exploits this redundancy for better compression ratios.

Additionally, reading back data for post-processing (e.g. extracting a time series at one pixel) requires decompressing full spatial slices one at a time when time-chunk=1.

**Recommendation:**
Use a time chunk that matches typical access patterns:
```python
# For daily output files: chunk 30 days together
time_chunk = min(30, n_timesteps) if n_timesteps > 1 else 1
chunksizes = (time_chunk, nrow, ncol)
```

For hourly outputs (sub-daily), consider `time_chunk = min(24, n_timesteps)` (one day of hours).

Make this configurable via a new setting:
```xml
<textvar name="OutputTimeChunkSize" value="30"/>
```

**Risk:** Low — chunking is internal to NetCDF format; does not affect data values.

**Estimated saving:** 10-30% better compression ratio; faster time-series extraction in post-processing.


---

### B3. Compression Level Setting

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/netcdf.py` |
| **Function** | `write_netcdf_header()` |
| **Impact** | **LOW-MEDIUM** |

**Current code:**
```python
zlib=True  # uses default complevel (typically 4 in netCDF4 library)
```

**Why it matters:**
The `complevel` parameter is not explicitly set, defaulting to whatever the netCDF4 library uses (usually 4). For operational runs where output I/O time is a bottleneck, a lower compression level (1-2) can significantly speed up writes at the cost of slightly larger files. For archival runs, a higher level (6-9) produces smaller files at the cost of write speed.

**Recommendation:**
Add an explicit compression level setting:
```python
comp_level = int(binding.get('OutputCompressionLevel', 4))
value = nf1.createVariable(..., zlib=True, complevel=comp_level, ...)
```

```xml
<textvar name="OutputCompressionLevel" value="4"/>
```

**Trade-off guidance:**
| Level | Write speed | File size | Use case |
|-------|-------------|-----------|----------|
| 1 | Fast | Larger (+20%) | Real-time forecasting |
| 4 | Balanced | Baseline | General use |
| 6-9 | Slow | Smaller (-10-20%) | Long-term archival |

**Estimated saving:** Configurable — up to 20% smaller files (level 6+) or 30% faster writes (level 1).


---

### B4. `compressArray` Forces float64 on All Arrays

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/add1.py` (line ~291) |
| **Function** | `compressArray()` |
| **Impact** | **MEDIUM** (memory footprint) |

**Current code:**
```python
return mapC.astype(float)  # float = float64 in NumPy
```

**Why it matters:**
Every map loaded through `compressArray` is cast to float64 regardless of its original dtype. This includes:
- Boolean masks (could be bool/int8 → 1 byte becomes 8 bytes)
- Integer maps like LDD, land-use classes (int8/int16 → float64)
- Maps read as float32 from NetCDF files (4 bytes → 8 bytes)

For EFAS with ~1.8M pixels, each unnecessary float64 promotion costs 14.4 MB (from float32) or 12.6 MB (from int8). With dozens of static maps loaded at initialization, this adds up to 200-500 MB of wasted memory.

**Recommendation:**
Preserve the input dtype or allow explicit specification:
```python
def compressArray(map, pcr=True, name=None, force_load_with_nans=False, dtype=None):
    # ... existing logic ...
    if dtype is not None:
        return mapC.astype(dtype)
    elif hasattr(mapC, 'dtype') and not np.issubdtype(mapC.dtype, np.floating):
        # Keep integer/boolean maps in their native type
        return mapC
    else:
        return mapC.astype(np.float64)  # backward compatible default for float maps
```

For a less invasive change, at minimum avoid promoting boolean and integer maps:
```python
if np.issubdtype(mapC.dtype, np.integer) or np.issubdtype(mapC.dtype, np.bool_):
    return mapC
return mapC.astype(float)
```

**Risk:** Low if done carefully. Some downstream code may assume float64; a `grep` for `.astype(float)` patterns in dependent code should be checked.

**Estimated saving:** 200-500 MB RAM reduction for large EFAS/GloFAS domains.


---

### B5. MCT State Variables: Extra Arrays Per Pixel

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/hydrological_modules/routing.py` |
| **Variables** | `PrevCm0`, `PrevDm0`, `ChanQ_0`, `ChanM3_0` (MCT-specific state) |
| **Impact** | **LOW** |

**Why it matters:**
MCT routing introduces 4 additional full-domain float64 arrays as state variables:
- `PrevCm0` (Courant number) — only meaningful at MCT pixels
- `PrevDm0` (Reynolds number) — only meaningful at MCT pixels
- `ChanQ_0` (previous discharge copy) — full domain
- `ChanM3_0` (previous storage copy) — full domain

For EFAS (~1.8M pixels): 4 arrays * 1.8M * 8 bytes = ~57 MB. However, only ~5000 pixels are MCT pixels (0.3% of domain).

**Recommendation:**
Store `PrevCm0` and `PrevDm0` as MCT-only compressed arrays (5000 pixels) rather than full-domain arrays:
```python
# In MCTWave.__init__:
self.PrevCm0_mct = np.ones(num_mct_pixels)
self.PrevDm0_mct = np.zeros(num_mct_pixels)
```

Map between MCT-local and full-domain indices using the existing `mapping_mct` array. This reduces memory by ~25 MB for these two arrays alone.

For `ChanQ_0` and `ChanM3_0`: these are full-domain copies needed as "previous state" inputs. They could be eliminated by reorganizing the MCT call to read directly from `self.var.ChanQ` before kinematic routing overwrites it (restructure call order).

**Estimated saving:** 25-57 MB RAM.


---

### B6. Enable MapsCaching by Default for Static Maps

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisfloodSettings_reference.xml` |
| **Setting** | `MapsCaching` |
| **Impact** | **MEDIUM** (runtime), **LOW** (memory trade-off) |

**Current default:**
```xml
<textvar name="MapsCaching" value="False"/>
```

**Why it matters:**
When `MapsCaching` is `False`, the `XarrayChunked` reader is used for forcing data. When `True`, the `XarrayCached` class (which uses `@Cache` decorator) stores the full dataset in memory, avoiding repeated disk reads.

For static maps loaded via `loadmap()`, caching avoids re-reading the same NetCDF file if it is referenced multiple times (e.g. soil parameters used in both initialization and dynamic sections).

**Recommendation:**
Enable caching by default:
```xml
<textvar name="MapsCaching" value="True"/>
```

For memory-constrained environments, document the memory cost and allow users to disable it.

**Memory cost:** For EFAS forcing data (5 variables, 1.8M pixels, 365 days, float32): ~13 GB. This is acceptable on modern HPC nodes (128-512 GB) but may be prohibitive on smaller machines.

**Estimated saving:** 10-30% faster initialization; eliminates repeated disk reads for static data during the run.


---

### B7. Output Variable Pruning: Map vs TSS Trade-offs

| Attribute | Detail |
|-----------|--------|
| **File** | Settings XML (user configuration) |
| **Impact** | **HIGH** (operational storage) |

**Why it matters:**
LISFLOOD can output dozens of 2D map variables at every timestep. For EFAS operational runs, the output volume is often the dominant storage cost. Many variables are only needed at specific gauge points (time series) rather than as full 2D maps.

**Recommendations:**

1. **Prefer TSS over Maps for point-based diagnostics**: Variables like discharge, water level, and lake/reservoir levels are typically only needed at gauge locations. Use TSS (Time Series) output instead of full maps:
   - Storage for 1 variable, 1000 gauges, 1 year daily: ~3 MB (TSS) vs ~2.4 GB (map, float32)
   - Factor 800x reduction

2. **Use monthly/yearly frequency for slow-changing variables**: Soil moisture, groundwater, snow cover change slowly. Report them monthly rather than daily:
   - 12x reduction in output volume for these variables

3. **Document output configurations**: Provide template settings files for common use cases:
   - `settings_minimal_output.xml` — discharge TSS only
   - `settings_operational.xml` — discharge maps + key state variables
   - `settings_research.xml` — full variable set

4. **Consider lossy compression for diagnostic maps**: For variables like soil moisture or temperature that are only used for visualization, NetCDF's `least_significant_digit` option can dramatically improve compression:
```python
value = nf1.createVariable(..., zlib=True, least_significant_digit=3)
# Keeps 3 significant digits, enables much better compression
```

**Estimated saving:** 50-95% output volume reduction depending on configuration.


---

### B8. Internal Computation Precision: Float64 Everywhere

| Attribute | Detail |
|-----------|--------|
| **Files** | All hydrological modules |
| **Impact** | **LOW** (memory), **LOW** (runtime on modern CPUs) |

**Current state:**
All internal state variables and computations use float64. This is the safe default for numerical stability, especially for:
- Accumulation variables over long simulations (mass balance)
- Channel routing where small flows interact with large storages
- The MCT solver which is sensitive to precision in Courant/Reynolds numbers

**Recommendation:**
Do NOT change internal precision to float32 for state variables. The risk of numerical drift over multi-year simulations outweighs the modest memory savings. Float64 arithmetic is nearly as fast as float32 on modern x86-64 CPUs (same SIMD width for scalar operations; only vectorised code benefits from float32's 2x throughput).

**Exception:** Intermediate temporary arrays that are not accumulated (e.g. `SideflowChan`, `SideflowDirect`) could safely use float32 if memory pressure is extreme, but the savings (~14 MB per temporary for EFAS) rarely justify the added complexity.

**Conclusion:** Keep float64 for internal computation. Focus memory optimization on B4 (dtype preservation for non-float maps) and B1 (output dtype).


---

## Part C — Prioritized Action Plan

| Rank | ID | Recommendation | Runtime Impact | Storage Impact | Complexity | Risk |
|------|----|----------------|----------------|----------------|------------|------|
| 1 | B9 | CF scale/offset packing (int16 output) | ~5% (I/O) | **75-90%** | Medium | Low |
| 2 | B1 | Change default OutputMapsDataType to float32 | ~5% (I/O) | **50%** | Low | None |
| 2 | A11 | MCT: Replace linear CalibPoints scan with boolean lookup | 5-15% MCT | — | Low | None |
| 3 | A2 | MCT: Pre-compute ANalv (arctan) | 2-5% MCT | — | Low | None |
| 4 | A3 | Kinematic wave: Replace numexpr with Numba helper | 5-10% routing | — | Medium | Low |
| 5 | B2 | Optimize NetCDF output time chunk size | 5% (I/O) | **10-30%** | Low | None |
| 6 | A4 | Routing: Pre-allocate scratch buffers, reduce .copy() | 3-8% routing | — | Medium | Low |
| 7 | B4 | compressArray: Preserve input dtype | — | **200-500 MB** | Low | Low |
| 8 | A6 | Surface routing: Batch 3 kinematic calls | 10-25% surface | — | Medium | Low |
| 9 | B7 | Output variable pruning (TSS vs Maps) | 5-15% (I/O) | **50-95%** | Config only | None |
| 10 | A1 | MCT: Better initial guess / vectorise batches | 10-20% MCT | — | High | Medium |
| 11 | B3 | Add configurable compression level | ±10% (I/O) | **±20%** | Low | None |
| 12 | A5 | Numba AOT / warm-up script | 10-30s startup | — | Medium | Low |
| 13 | B6 | Enable MapsCaching by default | 10-30% init | +memory | Low | Low |
| 14 | A8 | Async chunk prefetch for forcing I/O | 1-5% | — | Medium | Low |
| 15 | A9 | Increase OutputMapsChunks / enable async writes | 5-15% (I/O) | — | Low | Low |
| 16 | A7 | Resolve Numba/numexpr thread contention | 2-5% | — | Low | None |
| 17 | A12 | Water balance: reduce bincount calls | 1-3% | — | Low | None |
| 18 | A10 | Dynamic loop: cache options, reduce stdout | 1-2% | — | Low | None |
| 19 | B5 | MCT: Compress PrevCm0/PrevDm0 to MCT-only arrays | — | **25-57 MB** | Medium | Low |


---

## Part D — Quick Wins (Implementable in < 1 day each)

### D1. Change default output dtype (B1)
**File:** `src/lisfloodSettings_reference.xml`
```diff
- <textvar name="OutputMapsDataType" value="float64"/>
+ <textvar name="OutputMapsDataType" value="float32"/>
```

### D2. Pre-compute ANalv in MCT (A2)
**File:** `src/lisflood/hydrological_modules/mct.py`

In `MCTWave.__init__()`, add:
```python
self.ANalv = np.arctan(1.0 / ChanSdXdY)
```

Add `ANalv` as a parameter to `mct_routing()` and in the inner loop replace:
```python
ANalv = np.arctan(1 / ChanSdXdY[kinpix])
```
with:
```python
ANalv = precomputed_ANalv[kinpix]
```

### D3. Replace CalibPoints linear scan with boolean array (A11)
**File:** `src/lisflood/hydrological_modules/mct.py`

In `MCTWave.__init__()` or `routing.initialMCT()`:
```python
num_pixels = len(ChanLength)
is_calib_point = np.zeros(num_pixels, dtype=np.bool_)
if len(CalibPointsIds) > 0:
    is_calib_point[CalibPointsIds] = True
```

Pass `is_calib_point` to `mct_routing` and replace:
```python
if np.any(CalibPointsIds == ups_pix):
```
with:
```python
if is_calib_point[ups_pix]:
```

### D4. Add compression level setting (B3)
**File:** `src/lisflood/global_modules/netcdf.py`, in `write_netcdf_header()`:
```python
comp_level = int(binding.get('OutputCompressionLevel', 4))
value = nf1.createVariable(var_name, dtype, dims, zlib=True, complevel=comp_level, fill_value=-9999, chunksizes=chunks)
```

### D5. Increase default OutputMapsChunks (A9)
**File:** `src/lisfloodSettings_reference.xml`
```diff
- <textvar name="OutputMapsChunks" value="1"/>
+ <textvar name="OutputMapsChunks" value="30"/>
```


---

## Part E — Changes from Previous Report

| Previous Recommendation | Status | Notes |
|------------------------|--------|-------|
| Change OutputMapsDataType to float32 | **Still valid** | Retained as #1 priority |
| Optimize NetCDF time chunk sizes | **Still valid** | Code unchanged; chunksizes=(1,nrow,ncol) persists |
| Add compression level setting | **Still valid** | Not yet implemented |
| Enable MapsCaching by default | **Still valid** | Still defaults to False |
| Preserve input dtype in compressArray | **Still valid** | `mapC.astype(float)` unchanged |
| Add async I/O for output writing | **Partially implemented** | `OutputMapsFactoryThreads` exists but is not enabled by default |
| Consider float32 for internal calculations | **Superseded** | Now explicitly recommended AGAINST (see B8) — risk outweighs benefit |

### New sections added (not in original report):

| Section | Reason |
|---------|--------|
| A1, A2, A11 | MCT routing module did not exist |
| A3 | numexpr usage in kinematic_wave_parallel.py is new |
| A4 | .copy() pattern in routing loop amplified by MCT additions |
| A5 | Numba cold-start now affects more functions (MCT adds 6 new @njit) |
| A6 | Surface routing now uses parallel kinematic wave (was PCRaster before) |
| A7 | Thread contention newly relevant with parallel soil + parallel routing |
| A10 | Dynamic loop analysis refreshed against current code |
| A12 | Water balance module rewritten with new bincount patterns |
| B5 | MCT-specific state variable overhead is new |
| B7 | Output pruning guidance (operational vs research) |
| B8 | Explicit recommendation against float32 internals |


---

## Appendix: Profiling Guidance

To validate the estimates in this report, the following profiling approach is recommended:

### Wall-clock timing per module
Add timing instrumentation in `Lisflood_dynamic.py`:
```python
import time
t0 = time.perf_counter()
self.readmeteo_module.dynamic()
t_meteo = time.perf_counter() - t0

t0 = time.perf_counter()
self.soilloop_module.dynamic_soil()
t_soil = time.perf_counter() - t0

# ... etc for each module call
```

### Numba kernel timing
Use `numba.core.config.DEVELOPER_MODE = 1` and Numba's built-in timing, or wrap calls:
```python
t0 = time.perf_counter()
kwpt.kinematicRouting(...)
t_kin = time.perf_counter() - t0
```

### Memory profiling
Use `tracemalloc` or `memory_profiler` to identify peak memory usage:
```python
import tracemalloc
tracemalloc.start()
# ... run model ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

### I/O profiling
Monitor disk I/O with system tools (`iostat`, `iotop`) or Python's `cProfile` focused on netCDF4 calls.

---

*Report generated: July 2026*
*Codebase version: current HEAD (post-MCT integration)*
*Previous report: `lisflood_optimization_report.md` (I/O-focused, pre-MCT)*

---

### B9. CF-Convention Scale/Offset Packing (int16 storage of float data)

| Attribute | Detail |
|-----------|--------|
| **File** | `src/lisflood/global_modules/netcdf.py` |
| **Function** | `write_netcdf_header()` |
| **Impact** | **HIGH** (75% output storage reduction vs float64; 50% vs float32) |

**Current state:**
Output variables are stored as raw floating-point values (float64 or float32). No packing is applied.

**What is scale/offset packing?**
The CF conventions define two variable attributes — `scale_factor` and `add_offset` — that allow floating-point data to be stored as smaller integer types (typically int16 or uint16). On read, the client library automatically reconstructs the original value:

```
unpacked_value = packed_value * scale_factor + add_offset
```

A 16-bit integer provides 65536 distinct values. By choosing `scale_factor` and `add_offset` to cover the physical range of the variable, you get fixed-precision storage at **2 bytes per value** instead of 4 (float32) or 8 (float64).

**Why it matters:**
- float64 → int16: **75% reduction** (8 bytes → 2 bytes per value)
- float32 → int16: **50% reduction** (4 bytes → 2 bytes per value)
- Combined with zlib compression, the actual on-disk savings can exceed 80% because integer data with limited range compresses far better than floating-point data.
- This is standard practice in climate/meteorological data (CMIP6, ERA5, EFAS forcing data already use this).

**Variable-specific packing parameters:**

| Variable | Physical Range | scale_factor | add_offset | Precision | Suitable? |
|----------|---------------|--------------|------------|-----------|-----------|
| Discharge (m³/s) | 0 – 100,000 | 1.53 | 50,000 | ±0.8 m³/s | Yes (large rivers) |
| Discharge (m³/s) | 0 – 10,000 | 0.153 | 5,000 | ±0.08 m³/s | Yes (medium rivers) |
| Soil Moisture (fraction) | 0 – 1 | 1.53e-5 | 0.5 | ±8e-6 | Yes |
| Snow Water Equiv. (mm) | 0 – 2000 | 0.031 | 1000 | ±0.015 mm | Yes |
| Temperature (°C) | -50 – +50 | 0.00153 | 0 | ±0.001 °C | Yes |
| ET (mm/day) | 0 – 20 | 3.05e-4 | 10 | ±1.5e-4 mm | Yes |
| Water Level (m) | -5 – +20 | 3.82e-4 | 7.5 | ±0.2 mm | Yes |
| Groundwater (mm) | 0 – 5000 | 0.076 | 2500 | ±0.04 mm | Yes |

**Implementation:**

In `write_netcdf_header()`, add packing when a packing configuration is provided:

```python
# Determine packing based on variable metadata or user settings
packing = binding.get('OutputPacking', 'none')  # 'none', 'int16', 'auto'

if packing == 'int16' and frequency is not None:
    # Use variable-specific range or a safe default
    vmin, vmax = get_variable_range(var_name)  # lookup table
    scale = (vmax - vmin) / 65534.0  # leave room for fill_value
    offset = vmin + scale * 32767.0
    
    value = nf1.createVariable(var_name, 'i2', ('time', dim_lat_y, dim_lon_x),
                               zlib=True, fill_value=-32767,
                               chunksizes=(time_chunk, nrow, ncol))
    value.scale_factor = scale
    value.add_offset = offset
else:
    # Current behaviour (float32 or float64)
    value = nf1.createVariable(var_name, dtype, ('time', dim_lat_y, dim_lon_x),
                               zlib=True, fill_value=-9999,
                               chunksizes=(1, nrow, ncol))
```

The write step must also pack the data before storing:
```python
# In NetcdfStepsWriter.write() or equivalent:
if hasattr(nf1.variables[self.map_name], 'scale_factor'):
    scale = nf1.variables[self.map_name].scale_factor
    offset = nf1.variables[self.map_name].add_offset
    packed = np.round((map_np - offset) / scale).astype(np.int16)
    packed[map_np == -9999] = -32767  # fill value
    nf1.variables[self.map_name][step, :, :] = packed
else:
    nf1.variables[self.map_name][step, :, :] = map_np
```

**Settings XML:**
```xml
<textvar name="OutputPacking" value="int16"/>
<!-- Options: "none" (default, current behaviour), "int16" (CF scale/offset packing) -->
```

**Compatibility:**
- All modern NetCDF readers (xarray, CDO, NCO, QGIS, Python netCDF4) automatically apply `scale_factor` and `add_offset` on read — no user action needed.
- CF-compliant: follows CF-1.6+ conventions exactly.
- Backward compatible: if `OutputPacking=none`, behaviour is unchanged.

**Risks:**
- **Precision loss**: int16 provides ~4.8 significant digits (vs ~7 for float32, ~15 for float64). For most hydrological variables this is adequate. For variables with very large dynamic range (e.g. discharge spanning 0.001 to 100,000 m³/s), consider using per-timestep adaptive scaling or splitting into sub-ranges.
- **State/restart files should NOT be packed**: Warm-start state variables (used to restart the model) must retain full float64 precision to avoid drift. Only apply packing to reporting/output maps.

**Estimated saving:**
- vs current float64 default: **75% output file size reduction**
- vs float32: **50% additional reduction on top of B1**
- Combined with zlib (already enabled): effective on-disk ratios of 85-90% reduction are achievable

