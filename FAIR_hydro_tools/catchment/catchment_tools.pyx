import numpy as np

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

def downstreamToUpstreamLookup(long[::1] downstream_lookup, unsigned int max_num_ups):
    cdef:
        unsigned long ups_p, num_pixs = downstream_lookup.size
        long downs_p
        long[:,::1] upstream_lookup = -np.ones((num_pixs, max_num_ups), int)
        unsigned int[::1] ups_count = np.zeros(num_pixs, np.uintc)
    for ups_p in range(num_pixs):
        downs_p = downstream_lookup[ups_p]
        if downs_p != -1:
            upstream_lookup[downs_p,ups_count[downs_p]] = ups_p
            ups_count[downs_p] += 1
    return np.asarray(upstream_lookup)

def streamCumul(double[::1] data, long[::1] downstream_lookup, long[:,::1] upstream_lookup, unsigned char[::1] completed, unsigned long[::1] headwaters,\
                unsigned int[::1] num_upstreams, unsigned long num_done):
    cdef:
        double[::1] cumulated = data.copy()
        unsigned long i, n, u, num_pixs = data.size, h = 0, p = headwaters[h]
    # drainage network search
    while num_done < num_pixs:
        # check if pixel is completed -> cases
        if completed[p]: # 1) completed pixel -> check if it has a downstream pixel
            if downstream_lookup[p] == -1: # 1.1) river mouth pixel draining to the sea -> go to next headwater
                h += 1
                p = headwaters[h]
            else: # 1.2) non river mouth pixel -> go to downstream one
                p = downstream_lookup[p]
        else: # 2) non completed pixel -> check whether all upstream pixels are completed
            n = num_upstreams[p]
            i = 0
            while i < n and completed[upstream_lookup[p,i]]:
                i += 1
            if i == n: # 2.1) all upstream pixels are completed -> complete the pixel -> go to downstream one
                completed[p] = True
                num_done += 1
                for u in range(n):
                    cumulated[p] += cumulated[upstream_lookup[p,u]]
            else: # 2.2) go to next headwater (note: going to first non-complete upstream pixel performed worse - need for bookkeeping?)
                h += 1
                p = headwaters[h]
    return np.asarray(cumulated)

#def streamCumul_2(double[::1] data, long[::1] downstream_lookup, long[:,::1] upstream_lookup, unsigned char[::1] completed, unsigned long[::1] headwaters,\
#                  unsigned int[::1] num_upstreams, unsigned long num_done):
#    '''MORE ROBUST APPROACH BUT THE num_complete_upstream BOOKKEEPING NEEDS TO BE OPTIMISED'''
#    cdef:
#        double[::1] cumulated = data.copy()
#        unsigned long h, u, num_pixs = data.size, num_heads = headwaters.size
#        unsigned long[::1] num_complete_upstream = np.zeros(num_pixs, np.uint64)
#        long p
#    for h in headwaters:
#        num_complete_upstream[downstream_lookup[h]] += 1
#    h = 0
#    while num_done < num_pixs:
#        p = downstream_lookup[headwaters[h]]
#        while p != -1:
#            if completed[p]:
#                p = downstream_lookup[p]
#            elif num_complete_upstream[p] == num_upstreams[p]:
#                for u in range(num_upstreams[p]):
#                    cumulated[p] += cumulated[upstream_lookup[p,u]]
#                completed[p] = True
#                num_done += 1
#                p = downstream_lookup[p]
#                if p != -1:
#                    num_complete_upstream[p] += 1
#            else:
#                break
#        h += 1
#    return np.asarray(cumulated)

def setUpstreamRoutedKinematic(long[::1] pixels_routed, long[::1] downstream_lookup, long[:,::1] upstream_lookup, unsigned char[:,::1] upstream_routed):
    """Called by catchment.orderKinematicRouting"""
    cdef:
        long downs_pix, pix, ups_index
    for pix in pixels_routed:
        downs_pix = downstream_lookup[pix]
        if downs_pix != -1:
            ups_index = 0
            while upstream_lookup[downs_pix,ups_index] != pix:
                ups_index += 1
            upstream_routed[downs_pix,ups_index] = True
