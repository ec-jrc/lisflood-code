"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""

from functools import wraps


def counted(fn):
    def wrapper(*args, **kwargs):
        wrapper.called += 1
        return fn(*args, **kwargs)

    wrapper.called = 0
    wrapper.__name__ = fn.__name__
    return wrapper


def cached(f):
    _cache = {}

    @wraps(f)
    def _decorator(args):
        args = tuple(args)
        if args not in _cache:
            _cache[args] = f(args)
        return _cache[args]

    return _decorator


def iocache(obj):
    cache = {}

    found = 0

    @wraps(obj)
    def iocache_wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)

        if key not in cache:
            my_obj = obj(*args, **kwargs)
            if not isinstance(my_obj, float):
                cache[key] = my_obj
                to_return = cache[key]
            else:
                return my_obj
        else:
            nonlocal found
            found += 1
            to_return = cache[key]
        return to_return

    def iocache_clear():
        print('Clearing cache')
        cache.clear()
        nonlocal found
        found = 0

    def iocache_size():
        return len(cache)

    def iocache_found():
        nonlocal found
        return found

    def iocache_info():
        print('Caching {}'.format(obj))
        print('Number of items cached: {}'.format(iocache_size()))
        print('Number of items retrieved: {}'.format(iocache_found()))
        print('Keys:')
        for key in cache.keys():
            print('   - {}'.format(key))

    iocache_wrapper.iocache_clear = iocache_clear
    iocache_wrapper.iocache_found = iocache_found
    iocache_wrapper.iocache_info = iocache_info
    iocache_wrapper.iocache_size = iocache_size

    return iocache_wrapper