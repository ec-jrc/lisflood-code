"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

Parallel implementation of the kinematic wave routing.
This module provides tools to pre-process the flow direction matrix, and the kinematicWave class that
solves the kinematic wave equation. Most functions and methods call functions in the Numba module
kinematic_wave_parallel_tools.py, for performance reasons.
Parallelisation is achieved by grouping the pixels in ordered sets. Within each set, provided that
pixelsm in previous sets have already been routed, pixels can be routed independently of each other
and thus in parallel. For further details, see the method kinematicWave._setRoutingOrders.
"""
from __future__ import absolute_import, print_function, unicode_literals

__author__ = "Emiliano Gelati"
__contact__ = "emiliano.gelati@ec.europa.eu"
__version__ = "1.0"
__date__ = "2016/06/01"

import os
import glob
import warnings
from multiprocessing import cpu_count
from platform import system

import numpy as np
import pandas as pd
import numexpr as nx

from ..global_modules.errors import LisfloodWarning

from . import kinematic_wave_parallel_tools as kwpt

# -------------------------------------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------------------------------------

IX_ADDS = np.array([(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]) # flow directions (row and column shifts in coordinate mesh)
SEA_CODE = 0 # Value for sea pixel in LISFLOOD flow direction matrix
FLOW_CODE = [2, 3, 6, 9, 8, 7, 4, 1, 5] # Flow directions according to LISFLOOD encoding (see IX_ADDS for directions expressed as row/column shifts)



# -------------------------------------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------------------------------------

def rebuildFlowMatrix(compressed_encoded_ldd, land_mask):
    """"""
    encoded_flow_dir = SEA_CODE * np.ones(land_mask.shape, compressed_encoded_ldd.dtype)
    encoded_flow_dir[land_mask] = compressed_encoded_ldd
    return encoded_flow_dir

def decodeFlowMatrix(encoded):
    '''Converts LISFLOOD flow matrix values (FLOW_CODE) to flow directions (0 to 7, see IX_ADDS)'''
    decoded = np.empty(encoded.shape, int)
    encoded[encoded == SEA_CODE] = FLOW_CODE[8]
    for old, new in zip(FLOW_CODE, range(9)):
        decoded[encoded == old] = new
    return np.ascontiguousarray(decoded)

def streamLookups(flow_dir, land_mask):
    '''
    Compute the downstream lookup vector for a D8 water flow channel network,
    i.e. the adjecency list of the directed graph describing flow direction from each pixel.
    Arguments:
        flow_dir (numpy.ndarray): LISFLOOD flow matrix values (FLOW_CODE).
        land_mask (numpy.ndarray): land mask on coordinate mesh.
    Returns:
        downstream lookup (numpy.ndarray): for each pixel, index of downstream pixel (-1 = none); size = num_pixels
        upstream lookup (numpy.ndarray): each row gives the immediately upstream pixels (-1 = fill value); size = num_pixels, max_ups_pixs <= 8
    '''
    flow_dir[~land_mask] = 8 # exceeds number of rows of IX_ADDS
    num_pixs = land_mask.sum()
    # Create 2D array of indices of land pixels (each index is unique)
    # The IDs are numbered from 0 to num_pixs-1
    land_points = -np.ones(land_mask.shape, int)
    land_points[land_mask] = np.arange(num_pixs, dtype=int)
    downstream_lookup, upstream_lookup = kwpt.upDownLookups(flow_dir, np.ascontiguousarray(land_mask).astype(np.uint8), land_points, num_pixs, IX_ADDS)
    max_num_ups_pixs = max(1, np.any(upstream_lookup != -1, 0).sum()) # maximum number of upstreams pixels
    return downstream_lookup, np.ascontiguousarray(upstream_lookup[:,:max_num_ups_pixs]).astype(int) 

def topoDistFromSea(downstream_lookup, upstream_lookup):
    """"""
    num_pixels = downstream_lookup.size
    topological_distance = - np.ones(num_pixels, int)
    is_outlet = np.zeros(num_pixels, bool)
    is_outlet[downstream_lookup == -1] = True
    distance = 1
    while (topological_distance == -1).any():
        to_track = np.logical_and(is_outlet, topological_distance == -1)
        topological_distance[to_track] = distance
        next_ups = np.unique(upstream_lookup[to_track])
        next_ups = next_ups[next_ups != -1]
        is_outlet[next_ups] = True
        distance += 1
    return topological_distance



# -------------------------------------------------------------------------------------------------
# CLASS
# -------------------------------------------------------------------------------------------------

class kinematicWave:
    """"""

    def __init__(self, compressed_encoded_ldd, land_mask, alpha_channel, beta, space_delta, time_delta, alpha_floodplains=None, flagnancheck=False, routing_dtype=np.float64):
        """"""
        # variable to avoid printing repeated warning messages
        self.kinematic_wave_warning_printed=False
        self.flagnancheck=flagnancheck
        # Routing precision for the kinematic numba kernel. float64 (default) is the
        # historical, bit-identical path. float32 halves the kernel's memory traffic
        # at the cost of a dtype-appropriate Newton tolerance (opt-in via the
        # `routingPrecision` setting). The MCT path and all reductions/coupling stay
        # float64; this flag only governs the narrow kinematic-kernel boundary.
        self.routing_dtype = np.dtype(routing_dtype)
        self.newton_tol = (kwpt.NEWTON_TOL if self.routing_dtype == np.float64
                           else kwpt.NEWTON_TOL_FLOAT32)
        # Parameters for the solution of the discretised Kinematic wave continuity equation
        self.alpha_channel = alpha_channel
        self.space_delta = space_delta
        self.inv_time_delta = 1 / time_delta
        self.beta = beta
        self.inv_beta = 1 / beta
        self.b_minus_1 = beta - 1
        self.a_dx_div_dt_channel = alpha_channel * space_delta / time_delta
        self.b_a_dx_div_dt_channel = beta * self.a_dx_div_dt_channel
        self.a_dx = alpha_channel * space_delta
        # If split-routing (floodplains)
        if alpha_floodplains is not None:
            self.alpha_floodplains = alpha_floodplains
            self.a_dx_div_dt_floodplains = alpha_floodplains * space_delta / time_delta
            self.b_a_dx_div_dt_floodplains = beta * self.a_dx_div_dt_floodplains
            self.a_dx_floodplains = alpha_floodplains * space_delta
        # Process flow direction matrix: downstream and upstream lookups, and routing orders
        flow_dir = decodeFlowMatrix(rebuildFlowMatrix(compressed_encoded_ldd, land_mask))
        self.downstream_lookup, self.upstream_lookup = streamLookups(flow_dir, land_mask)
        self.num_upstream_pixels = (self.upstream_lookup != -1).sum(1).astype(int) 
        # Routing order: decompose domain into batches; within each batch, pixels can be routed in parallel
        self._setRoutingOrders()

    def _setRoutingOrders(self):
        """Compute the kinematic wave routing order. Pixels are grouped in sets with the same order.
        Pixels in the same set are independent and can be routed in parallel. Sets must be processed in series, starting from order 0.
        Pixels are ordered topologically starting from the outlets, as in:
        Liu et al. (2014), A layered approach to parallel computing for spatially distributed hydrological modeling,
        Environmental Modelling & Software 51, 221-227.
        Order MAX is given to pixels with no downstream relations (outlets); order MAX-1 is given to
        pixels whose downstream pixels are all of order MAX; and so on."""
        ocean_topo_distance = topoDistFromSea(self.downstream_lookup, self.upstream_lookup)
        routing_order = ocean_topo_distance.max() - ocean_topo_distance
        self.pixels_ordered = pd.DataFrame({"pixels": np.arange(routing_order.size), "order": routing_order})
        try:
            self.pixels_ordered = self.pixels_ordered.sort_values(["order", "pixels"]).set_index("order").squeeze()
        except: # FOR COMPATIBILITY WITH OLDER PANDAS VERSIONS
            self.pixels_ordered = self.pixels_ordered.sort(["order", "pixels"]).set_index("order").squeeze()
        # Ensure output is always a Series, even if only one element
        if not isinstance(self.pixels_ordered, pd.DataFrame):
            self.pixels_ordered = pd.Series(self.pixels_ordered)

        order_counts = self.pixels_ordered.groupby(self.pixels_ordered.index).count()
        # calc number of sets (orders)
        stop = order_counts.cumsum()
        self.order_start_stop = np.column_stack((np.append(0, stop[:-1]), stop)).astype(int)
        # find start and end pixel in each order
        self.pixels_ordered = self.pixels_ordered.values.astype(int)
        # array containing all pixels organised by computation order

    def kinematicWaveRouting(self, discharge_avg, discharge, specific_lateral_inflow, section="main_channel"):
        """Kinematic wave routing: wrapper around kinematic_wave_parallel_tools.kinematicWave

        When ``routing_dtype`` is float64 (the default) this is the original,
        bit-identical path. When it is float32 the Newton solve runs in float32
        over float32 copies of the dynamic arrays, and the results are written
        back into the caller's float64 ``discharge``/``discharge_avg`` arrays in
        place (narrow boundary: everything outside the kernel stays float64).
        """
        # Lateral inflow (m3 s-1)
        lateral_inflow = nx.evaluate("q * dx", local_dict={"q": specific_lateral_inflow, "dx": self.space_delta})
        # Choose between main channel and floodplain routing
        if section == "main_channel":
            a_dx_div_dt = self.a_dx_div_dt_channel
            b_a_dx_div_dt = self.b_a_dx_div_dt_channel
            a_dx = self.a_dx
        elif section == "floodplains":
            a_dx_div_dt = self.a_dx_div_dt_floodplains
            b_a_dx_div_dt = self.b_a_dx_div_dt_floodplains
            a_dx = self.a_dx_floodplains
        else:
            raise Exception("The section parameter must be either 'main_channel' or 'floodplain'!")

        if self.routing_dtype == np.float64:
            # Historical path - unchanged (bit-identical). Only addition: the
            # Newton tolerance is now passed explicitly (== the former module
            # constant NEWTON_TOL = 1e-12), so results are identical.
            # Constant term in f(x) evaluation for Newton-Raphson method
            local_dict = {"a_dx_div_dt": a_dx_div_dt, "Qold": discharge, "b": self.beta, "lateral_inflow": lateral_inflow}
            constant = nx.evaluate("a_dx_div_dt * Qold ** b + lateral_inflow", local_dict=local_dict)
            # Solve the Kinematic wave equation
            kwpt.kinematicRouting(discharge_avg, discharge, lateral_inflow, constant, self.upstream_lookup,\
                                  self.num_upstream_pixels, self.pixels_ordered, self.order_start_stop,\
                                  self.inv_time_delta, self.beta, self.inv_beta, self.b_minus_1,\
                                  a_dx_div_dt, b_a_dx_div_dt, a_dx, kwpt.NEWTON_TOL)
        else:
            # --- float32 narrow-boundary path (opt-in) ---
            dt = self.routing_dtype
            # float32 copies of the dynamic arrays; the kernel mutates these in place.
            disch32 = discharge.astype(dt)
            disch_avg32 = discharge_avg.astype(dt)
            lat32 = lateral_inflow.astype(dt)
            # Constants coherent in dtype so numexpr/numba do not upcast to float64.
            a_dx_div_dt32 = a_dx_div_dt.astype(dt)
            b_a_dx_div_dt32 = b_a_dx_div_dt.astype(dt)
            a_dx32 = a_dx.astype(dt)
            # Constant term in f(x) evaluation for Newton-Raphson method
            constant = (a_dx_div_dt32 * disch32 ** dt.type(self.beta) + lat32).astype(dt)
            # Solve the Kinematic wave equation
            kwpt.kinematicRouting(disch_avg32, disch32, lat32, constant, self.upstream_lookup,\
                                  self.num_upstream_pixels, self.pixels_ordered, self.order_start_stop,\
                                  dt.type(self.inv_time_delta), dt.type(self.beta), dt.type(self.inv_beta),\
                                  dt.type(self.b_minus_1), a_dx_div_dt32, b_a_dx_div_dt32, a_dx32,\
                                  dt.type(self.newton_tol))
            # Cast results back into the caller's float64 arrays in place, so the rest
            # of routing.dynamic (storage recompute, MCT, mass balance, coupling) sees
            # float64 exactly as before.
            discharge[:] = disch32
            discharge_avg[:] = disch_avg32

        # NaN/Inf check runs for BOTH precision paths (the float64 path previously
        # ran it unconditionally; keep that behaviour).
        if self.flagnancheck:
            if self.kinematic_wave_warning_printed==False:
                if np.all(np.isfinite(discharge))==False:
                    warnings.warn(LisfloodWarning("Warning: NaN or Inf values after kinematicRouting module. Suggestion: please check the input maps (e.g. channel geometry and ldd)"))
                    self.kinematic_wave_warning_printed=True