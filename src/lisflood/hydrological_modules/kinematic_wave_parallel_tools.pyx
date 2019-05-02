"""
Collection of functions called by the Python module kinematic_wave_parallel.py. These functions are
implemented in Cython to achieve compiled-code performance when executing loops over numpy arrays.
To compile this Cython module to enable OpenMP multithreading, execute:
$ python compile_kinematic_wave_parallel_tools.py build_ext --inplace
Important: the module has to be compiled on the machine where the model is run - the resulting binary is not portable.
"""
__author__ = "Emiliano Gelati"
__contact__ = "emiliano.gelati@ec.europa.eu"
__version__ = "1.0"
__date__ = "2016/06/01"


import numpy as np
from cython import boundscheck, wraparound, cdivision
from cython.parallel import prange
from libc.math cimport fabs, fmax, fmin

cdef:
    double NEWTON_TOL = 1e-12 # Max allowed error in iterative solution
    long MAX_ITERS = 3000 # Max number of iterations
    double MIN_DISCHARGE = 1e-30 # Minimum allowed discharge value to avoid numerical instability


# -------------------------------------------------------------------------------------------------
# ROUTING FUNCTIONS
# -------------------------------------------------------------------------------------------------
@boundscheck(False)
@wraparound(False)
def kinematicRouting(double[::1] discharge, double[::1] lateral_inflow, double[::1] constant, long[:,::1] upstream_lookup,\
                     long[::1] num_upstream_pixels, long[::1] ordered_pixels, long[:,::1] start_stop, double beta, double inv_beta,\
                     double b_minus_1, double[::1] a_dx_div_dt, double[::1] b_a_dx_div_dt, long num_threads):
    """"""
    cdef:
        long order, index, first, last, num_orders = start_stop.shape[0]
    # Iterate through routing orders (sets of pixels for which the kinemativc wave can be solved independently and thus in parallel)
    for order in range(num_orders):
        first = start_stop[order,0]
        last = start_stop[order,1]
        for index in prange(first, last, nogil=True, schedule="dynamic", num_threads=num_threads):
            solve1Pixel(ordered_pixels[index], discharge, lateral_inflow, constant, upstream_lookup,\
                        num_upstream_pixels, a_dx_div_dt, b_a_dx_div_dt, beta, inv_beta, b_minus_1)

@boundscheck(False)
@wraparound(False)
@cdivision(True)
cdef void solve1Pixel(long pix, double[::1] discharge, double[::1] lateral_inflow, double[::1] constant,\
                      long[:,::1] upstream_lookup, long[::1] num_upstream_pixels, double[::1] a_dx_div_dt,\
                      double[::1] b_a_dx_div_dt, double beta, double inv_beta, double b_minus_1) nogil:
    """"""
    cdef:
        long ups_ix, count = 0
        double error, const_plus_ups_infl, a_cpui_pow_b_m_1, secant_bound, other_bound, previous_estimate = -1., upstream_inflow = 0.
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
        discharge[pix] = fmax(discharge[pix], NEWTON_TOL)
        error = closureError(discharge[pix], const_plus_ups_infl, a_dx_div_dt[pix], beta)
        count += 1
    # If iterations converge to NEWTON_TOL, set value to 0
    if discharge[pix] == NEWTON_TOL:
        discharge[pix] = 0

@boundscheck(False)
@wraparound(False)
cdef double closureError(double discharge, double upper_bound, double a_dx_div_dt, double beta) nogil:
    """"""
    return discharge + a_dx_div_dt * discharge**beta - upper_bound



# -------------------------------------------------------------------------------------------------
# FLOW DIRECTION MATRIX PRE-PROCESSING FUNCTIONS
# -------------------------------------------------------------------------------------------------
def updateUpstreamRouted(long[::1] pixels_routed, long[::1] downstream_lookup,\
                         long[:,::1] upstream_lookup, unsigned char[:,::1] upstream_routed):
    """Called by kinematic_wave_parallel.orderKinematicRouting to implement greedy pixel ordering starting from headwaters."""
    cdef:
        long downs_pix, pix, ups_index
    for pix in pixels_routed:
        downs_pix = downstream_lookup[pix]
        if downs_pix != -1:
            ups_index = 0
            while upstream_lookup[downs_pix,ups_index] != pix:
                ups_index += 1
            upstream_routed[downs_pix,ups_index] = True

def upDownLookups(long[:,::1] flow_d8, unsigned char[:,::1] land_mask, long[:,::1] land_points, long num_pixs, long[:,::1] ix_adds):
    '''Called by catchment.streamLookups'''
    cdef:
        long[::1] downstream_lookup = -np.ones(num_pixs, int)
        long[:,::1] upstream_lookup = -np.ones((num_pixs, 8), int)
        unsigned int[::1] ups_count = np.zeros(num_pixs, np.uintc)
        int src_row, src_col, dst_row, dst_col
        unsigned int ups_p, downs_p, num_row = flow_d8.shape[0], num_col = flow_d8.shape[1]
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
def immediateUpstreamInflow(double[::1] discharge, long[:,::1] upstream_lookup, long[::1] num_upstream_pixels):
    """"""
    cdef:
        long pix, ups_ix, num_pixels = discharge.size
        double [::1] inflow = np.zeros(num_pixels)
    for pix in range(num_pixels):
        for ups_ix in range(num_upstream_pixels[pix]):
            inflow[pix] += discharge[upstream_lookup[pix,ups_ix]]
    return np.asarray(inflow)