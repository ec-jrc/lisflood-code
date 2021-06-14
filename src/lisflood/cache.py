
from .global_modules.add1 import loadmap_cached
from .global_modules.netcdf import XarrayCached


def cache_clear():
    XarrayCached.iocache_clear()
    loadmap_cached.iocache_clear()

def cache_size():
    count = 0
    count += XarrayCached.iocache_size()
    count += loadmap_cached.iocache_size()
    return count

def cache_info():
    XarrayCached.iocache_info()
    loadmap_cached.iocache_info()

def cache_found():
    count = 0
    count += XarrayCached.iocache_found()
    count += loadmap_cached.iocache_found()
    return count
