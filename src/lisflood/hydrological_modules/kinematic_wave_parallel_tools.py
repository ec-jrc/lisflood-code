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
def kinematicRouting(discharge_avg, discharge, lateral_inflow, constant, upstream_lookup,\
                     num_upstream_pixels, ordered_pixels, start_stop, inv_time_delta, beta, inv_beta,\
                     b_minus_1, a_dx_div_dt, b_a_dx_div_dt, a_dx):
    """
    This function performs the kinematic wave routing algorithm to simulate the movement of water through a network of interconnected channels.
    :param discharge:
    :param lateral_inflow:
    :param constant:
    :param upstream_lookup:
    :param num_upstream_pixels:
    :param ordered_pixels:
    :param start_stop:
    :param beta:
    :param inv_beta:
    :param b_minus_1:
    :param a_dx_div_dt:
    :param b_a_dx_div_dt:
    :param a_dx: ChannelAlpha * ChanLength
    :return:
    """
    num_orders = start_stop.shape[0]
    # Iterate through each routing order (sets of pixels for which the kinemativc wave can be solved independently and thus in parallel)
    for order in range(num_orders):
        first = start_stop[order,0]
        last = start_stop[order,1]
        # Iterate through each pixel in the current order in parallel
        for index in prange(first, last):
            # Solve the kinematic wave for the current pixel
            solve1Pixel(ordered_pixels[index], discharge_avg, discharge, lateral_inflow, constant, upstream_lookup,\
                        num_upstream_pixels, a_dx_div_dt, b_a_dx_div_dt, inv_time_delta, beta, inv_beta, b_minus_1, a_dx)

@njit(nogil=True, fastmath=False, cache=True)
def solve1Pixel(pix, discharge_avg, discharge, lateral_inflow, constant,\
                      upstream_lookup, num_upstream_pixels, a_dx_div_dt,\
                      b_a_dx_div_dt, inv_time_delta, beta, inv_beta, b_minus_1, a_dx):
    """
    Te Chow et al. 1988 - Applied Hydrology - Chapter 9.6
    :param pix:
    :param discharge_avg: average outflow discharge
    :param discharge: instantaneous outflow discharge
    :param lateral_inflow:
    :param constant:
    :param upstream_lookup:
    :param num_upstream_pixels:
    :param a_dx_div_dt:
    :param b_a_dx_div_dt:
    :param inv_time_delta: 1/DtRouting
    :param beta:
    :param inv_beta:
    :param b_minus_1:
    :param a_dx: ChannelAlpha * ChanLength
    :return:
    """
    count = 0
    previous_estimate = -1.0
    upstream_inflow = 0.0
    upstream_inflow_avg = 0.0

    # volume of water in channel at beginning of computation step
    channel_volume_start = a_dx * discharge[pix]**beta

    # Inflow from upstream pixels
    for ups_ix in range(num_upstream_pixels[pix]):
        upstream_inflow += discharge[upstream_lookup[pix,ups_ix]]
        upstream_inflow_avg += discharge_avg[upstream_lookup[pix, ups_ix]]
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

    # cmcheck
    # avoid negative discharge
    if discharge[pix] < 0:
        discharge[pix] = 0
    # volume of water in channel at end of computation step
    channel_volume_end = a_dx * discharge[pix]**beta
    # mass water balance to calc average outflow
    discharge_avg[pix] = upstream_inflow_avg + lateral_inflow + (channel_volume_start - channel_volume_end) * inv_time_delta


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
    """
    Called by kinematic_wave_parallel.orderKinematicRouting to implement greedy pixel ordering starting from headwaters.
    Update the boolean array upstream_routed to mark the upstream pixels that have already been routed.
    The function loops over each pixel in pixels_routed, identifies its downstream pixel, and sets the corresponding
    element of upstream_routed to True. This is achieved by finding the index of the current pixel in the upstream_lookup
    array of the downstream pixel and setting the corresponding element of upstream_routed to True.

    Parameters:
    -----------
    pixels_routed : array-like
        1D array of integers representing pixels that have already been routed.
    downstream_lookup : array-like
        1D array of integers representing the downstream pixel index for each pixel.
    upstream_lookup : array-like
        2D array of integers representing the upstream pixel index for each downstream pixel and each of its upstream pixels.
    upstream_routed : array-like
        2D boolean array representing whether each upstream pixel has already been routed.

    Returns:
    --------
    None
    :param pixels_routed:
    :param downstream_lookup:
    :param upstream_lookup:
    :param upstream_routed:
    :return:
    """
    for pix in pixels_routed:
        # Find the downstream pixel index for the current pixel
        downs_pix = downstream_lookup[pix]
        if downs_pix != -1:
            # Find the index of the current pixel among its upstream pixels
            ups_index = 0
            while upstream_lookup[downs_pix,ups_index] != pix:
                ups_index += 1
            # Mark the upstream pixel as routed
            upstream_routed[downs_pix,ups_index] = True

@njit(nogil=True, fastmath=False, cache=True)
def upDownLookups(flow_d8, land_mask, land_points, num_pixs, ix_adds):
    """
    Called by catchment.streamLookups
    Create lookups of pixels upstream and downstream of each pixel in a catchment.
    These arrays are used to determine the flow paths of water from a source pixel to all the pixels downstream and upstream of it, respectively.
    The function loops through each pixel in the dataset and checks whether it has a downstream neighbor in the direction of its flow_d8 value.
    If it does, it calculates the ID of the downstream pixel using the ix_adds array and checks whether the downstream pixel is also a land pixel
    (i.e. it is not water or outside the dataset). If both pixels are land pixels, the function updates the downstream_lookup and upstream_lookup
    arrays with the IDs of the upstream and downstream pixels, respectively. The function keeps track of the number of upstream neighbors for
    each downstream pixel using the ups_count array.

    Parameters:
    -----------
    flow_d8 : long[:,::1]
        2D array of D8 flow direction codes
    land_mask : unsigned char[:,::1]
        2D array of 0/1 indicating whether each pixel is land or not
    land_points : long[:,::1]
        2D array of indices of land pixels (each index is unique).
        The IDs are numbered from 0 to num_pixs - 1.
    num_pixs : long
        Number of pixels in the catchment
    ix_adds : long[:,::1]
        2D array of pixel coordinates to add to a source pixel to get destination pixel
        in a given direction, given as (row, col) pairs

    Returns:
    --------
    downstream_lookup : long[::1]
        1D array of indices of downstream pixels for each pixel in the catchment
    upstream_lookup : long[:,::1]
        2D array of indices of upstream pixels for each pixel in the catchment
    :param flow_d8:
    :param land_mask:
    :param land_points:
    :param num_pixs:
    :param ix_adds:
    :return:
    """
    downstream_lookup = -np.ones(num_pixs)
    upstream_lookup = -np.ones((num_pixs, 8))
    ups_count = np.zeros(num_pixs, np.uintc)
    num_row = flow_d8.shape[0]
    num_col = flow_d8.shape[1]
    # Loop over every pixel in the catchment
    for src_row in range(num_row):
        for src_col in range(num_col):
            # If the flow direction is less than 8 (i.e. the pixel is part of the catchment)
            if flow_d8[src_row,src_col] < 8:
                # Compute the destination pixel coordinates based on flow direction
                dst_row = src_row + ix_adds[flow_d8[src_row,src_col],0]
                dst_col = src_col + ix_adds[flow_d8[src_row,src_col],1]
                # Check if the destination pixel is within the boundaries of the land_mask
                # and is itself a land pixel
                if dst_row != -1 and dst_col != -1 and dst_row != num_row and dst_col != num_col and land_mask[dst_row,dst_col]:
                    # Get the indices of the source and destination pixels in the land_points array
                    ups_p = land_points[src_row,src_col]
                    downs_p = land_points[dst_row,dst_col]
                    # Assign the downstream pixel index to the upstream_lookup array for the source pixel
                    downstream_lookup[ups_p] = downs_p
                    # Assign the upstream pixel index to the upstream_lookup array for the destination pixel
                    # and increment the counter for the number of upstream pixels
                    upstream_lookup[downs_p,ups_count[downs_p]] = ups_p
                    ups_count[downs_p] += 1

    # Return the downstream and upstream lookup arrays
    return np.asarray(downstream_lookup), np.asarray(upstream_lookup)



# -------------------------------------------------------------------------------------------------
# MISCELLANOUS TOOLS
# -------------------------------------------------------------------------------------------------
@njit(nogil=True, fastmath=False, cache=True)
def immediateUpstreamInflow(discharge, upstream_lookup, num_upstream_pixels):
    """Calculate the immediate upstream inflow for each pixel in a river network.
    The implementation of the function is as follows:
    A new 1D NumPy array of type double called inflow is created with the same length as discharge, and is initialized to all zeros.
    A loop over all the pixels in the river network is started, using the range() function and the num_pixels variable (which is set to the length of discharge).
    Inside the loop, another loop over the upstream pixels for the current pixel is started, using the range() function and the num_upstream_pixels[pix] variable.
    Inside the inner loop, the inflow for the current pixel is updated by adding the discharge of the upstream pixel, which is retrieved using the upstream_lookup array.
    Finally, the inflow array is returned as a NumPy array.

    Args:
        discharge: A 1D NumPy array of type double that represents the discharge (flow rate) for each pixel in the river network.
        upstream_lookup: A 2D NumPy array of type long that represents the upstream routing of each pixel in the river network.
        num_upstream_pixels: A 1D NumPy array of type long that represents the number of upstream pixels for each pixel in the river network.

    Returns:
        A 1D NumPy array of type double that represents the immediate upstream inflow for each pixel in the river network.

    :param discharge:
    :param upstream_lookup:
    :param num_upstream_pixels:
    :return:
    """
    num_pixels = discharge.size
    inflow = np.zeros(num_pixels)
    # Loop over all the pixels in the river network
    for pix in range(num_pixels):

        # Loop over the upstream pixels for the current pixel
        for ups_ix in range(num_upstream_pixels[pix]):

            # Update the inflow for the current pixel by adding the discharge of the upstream pixel
            inflow[pix] += discharge[upstream_lookup[pix,ups_ix]]

    # Return the inflow array as a NumPy array
    return np.asarray(inflow)

