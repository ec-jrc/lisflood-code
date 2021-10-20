
from .global_modules.add1 import loadmap_cached
from .global_modules.netcdf import XarrayCached, read_lat_from_template
import copy


def cache_clear():
    XarrayCached.iocache_clear()
    loadmap_cached.iocache_clear()
    read_lat_from_template.iocache_clear()

def cache_size():
    count = 0
    count += XarrayCached.iocache_size()
    count += loadmap_cached.iocache_size()
    count += read_lat_from_template.iocache_size()
    return count

def cache_info():
    XarrayCached.iocache_info()
    loadmap_cached.iocache_info()
    read_lat_from_template.iocache_info()

def cache_found():
    count = 0
    count += XarrayCached.iocache_found()
    count += loadmap_cached.iocache_found()
    count += read_lat_from_template.iocache_found()
    return count

def cache_extract():
    extracted_cache = {
        "XarrayCached": XarrayCached.iocache_extract(),
        "loadmap_cached": loadmap_cached.iocache_extract(),
        "read_lat_from_template" : read_lat_from_template.iocache_extract()
    }
    return copy.deepcopy(extracted_cache)

def cache_apply(cachedic):
    XarrayCached.iocache_apply(cachedic["XarrayCached"])
    loadmap_cached.iocache_apply(cachedic["loadmap_cached"])
    read_lat_from_template.iocache_apply(cachedic["read_lat_from_template"])
