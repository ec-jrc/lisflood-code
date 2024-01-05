"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

Collection of functions called by the Python module kinematic_wave_parallel.py. 
"""

from math import fabs
import numpy as np
from numba import njit, prange
from builtins import max



NEWTON_TOL = 1e-12 # Max allowed error in iterative solution
MAX_ITERS = 3000 # Max number of iterations
MIN_DISCHARGE = 1e-30 # Minimum allowed discharge value to avoid numerical instability


# -------------------------------------------------------------------------------------------------
# ROUTING FUNCTIONS
# -------------------------------------------------------------------------------------------------
@njit(parallel=True, fastmath=False, cache=True)
def kinematicRouting(discharge, lateral_inflow, constant, upstream_lookup,\
                     num_upstream_pixels, ordered_pixels, start_stop, beta, inv_beta,\
                     b_minus_1, a_dx_div_dt, b_a_dx_div_dt):
    """"""
    num_orders = start_stop.shape[0]
    # Iterate through routing orders (sets of pixels for which the kinemativc wave can be solved independently and thus in parallel)
    for order in range(num_orders):
        first = start_stop[order,0]
        last = start_stop[order,1]
        for index in prange(first, last):
            solve1Pixel(ordered_pixels[index], discharge, lateral_inflow, constant, upstream_lookup,\
                        num_upstream_pixels, a_dx_div_dt, b_a_dx_div_dt, beta, inv_beta, b_minus_1)

@njit(nogil=True, fastmath=False, cache=True)
def solve1Pixel(pix, discharge, lateral_inflow, constant,\
                      upstream_lookup, num_upstream_pixels, a_dx_div_dt,\
                      b_a_dx_div_dt, beta, inv_beta, b_minus_1):
    """"""
    count = 0
    previous_estimate = -1.0
    upstream_inflow = 0.0
    # Inflow from upstream pixels
    for ups_ix in range(num_upstream_pixels[pix]):
        upstream_inflow += discharge[upstream_lookup[pix,ups_ix]]
    const_plus_ups_infl = upstream_inflow + constant[pix] # upstream_inflow + alpha*dx/dt*Qold**beta + dx*specific_lateral_inflow
    # If old discharge, upstream inflow and lateral inflow are below accuracy: set discharge to 0 and exit
    if const_plus_ups_infl <= NEWTON_TOL:
        discharge[pix] = 0
        return
    # Initial discharge guess using analytically derived boundary values
    a_cpui_pow_b_m_1 = b_a_dx_div_dt[pix] * const_plus_ups_infl**b_minus_1
    if a_cpui_pow_b_m_1 <= 1:
        secant_bound = const_plus_ups_infl / (1 + a_cpui_pow_b_m_1)
    else:
        secant_bound = const_plus_ups_infl / (1 + a_cpui_pow_b_m_1**inv_beta)
    other_bound = ((const_plus_ups_infl - secant_bound) / a_dx_div_dt[pix])**inv_beta
    discharge[pix] = (secant_bound + other_bound) / 2
    error = closureError(discharge[pix], const_plus_ups_infl, a_dx_div_dt[pix], beta)
    # Iterations
    while fabs(error) > NEWTON_TOL and discharge[pix] != previous_estimate and count < MAX_ITERS: # is previous_estimate useful?
        previous_estimate = discharge[pix]
        discharge[pix] -= error / (1 + b_a_dx_div_dt[pix] * discharge[pix]**b_minus_1)
        discharge[pix] = max(discharge[pix], NEWTON_TOL)
        error = closureError(discharge[pix], const_plus_ups_infl, a_dx_div_dt[pix], beta)
        count += 1
    # If iterations converge to NEWTON_TOL, set value to 0
    if discharge[pix] == NEWTON_TOL:
        discharge[pix] = 0
    # to simulate inf or nan: discharge[pix] = 1.0/0.0
    # with gil:
    #    got_valid_value = np.isfinite(discharge[pix])
    #    if got_valid_value==False:
    #          print(str(discharge[pix]) + ' found at pix:' + str(pix))

@njit(nogil=True, fastmath=False, cache=True)
def closureError(discharge, upper_bound, a_dx_div_dt, beta):
    """"""
    return discharge + a_dx_div_dt * discharge**beta - upper_bound



# -------------------------------------------------------------------------------------------------
# FLOW DIRECTION MATRIX PRE-PROCESSING FUNCTIONS
# -------------------------------------------------------------------------------------------------
@njit(nogil=True, fastmath=False, cache=True)
def updateUpstreamRouted(pixels_routed, downstream_lookup,\
                         upstream_lookup, upstream_routed):
    """Called by kinematic_wave_parallel.orderKinematicRouting to implement greedy pixel ordering starting from headwaters."""
    for pix in pixels_routed:
        downs_pix = downstream_lookup[pix]
        if downs_pix != -1:
            ups_index = 0
            while upstream_lookup[downs_pix,ups_index] != pix:
                ups_index += 1
            upstream_routed[downs_pix,ups_index] = True

@njit(nogil=True, fastmath=False, cache=True)
def upDownLookups(flow_d8, land_mask, land_points, num_pixs, ix_adds):
    '''Called by catchment.streamLookups'''
    downstream_lookup = -np.ones(num_pixs)
    upstream_lookup = -np.ones((num_pixs, 8))
    ups_count = np.zeros(num_pixs, np.uintc)
    num_row = flow_d8.shape[0]
    num_col = flow_d8.shape[1]
    for src_row in range(num_row):
        for src_col in range(num_col):
            if flow_d8[src_row,src_col] < 8:
                dst_row = src_row + ix_adds[flow_d8[src_row,src_col],0]
                dst_col = src_col + ix_adds[flow_d8[src_row,src_col],1]
                if dst_row != -1 and dst_col != -1 and dst_row != num_row and dst_col != num_col and land_mask[dst_row,dst_col]:
                    ups_p = land_points[src_row,src_col]
                    downs_p = land_points[dst_row,dst_col]
                    downstream_lookup[ups_p] = downs_p
                    upstream_lookup[downs_p,ups_count[downs_p]] = ups_p
                    ups_count[downs_p] += 1
    return np.asarray(downstream_lookup), np.asarray(upstream_lookup)



# -------------------------------------------------------------------------------------------------
# MISCELLANOUS TOOLS
# -------------------------------------------------------------------------------------------------
@njit(nogil=True, fastmath=False, cache=True)
def immediateUpstreamInflow(discharge, upstream_lookup, num_upstream_pixels):
    """"""
    num_pixels = discharge.size
    inflow = np.zeros(num_pixels)
    for pix in range(num_pixels):
        for ups_ix in range(num_upstream_pixels[pix]):
            inflow[pix] += discharge[upstream_lookup[pix,ups_ix]]
    return np.asarray(inflow)

