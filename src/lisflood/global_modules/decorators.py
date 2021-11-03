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
import copy


def counted(fn):
    def wrapper(*args, **kwargs):
        wrapper.called += 1
        return fn(*args, **kwargs)

    wrapper.called = 0
    wrapper.__name__ = fn.__name__
    return wrapper


def cached(f):
    """
    Simple cache for small objects like parsing options
    """

    _cache = {}

    @wraps(f)
    def _decorator(args):
        args = tuple(args)
        if args not in _cache:
            _cache[args] = f(args)
        return _cache[args]

    return _decorator


class Cache:
    """
    Class decorator used to cache large objects read from disk
    Mostly used for forcings and static maps
    """

    cache = {}
    found = {}

    def __init__(self, fn):
        self.name = fn.__name__
        self.fn = fn
        # we need to put the counter in a dict
        # or we lose the reference
        if self.name not in self.found:
            self.found[self.name] = 0

    def __call__(self, *args, **kwargs):

        key = '{}, {}, {}'.format(self.name, args, kwargs)

        if key not in self.cache:
            data = self.fn(*args, **kwargs)
            # we don't cache small objects (e.g. floats from loadmap)
            if isinstance(data, float):
                return_data = data
            else:
                self.cache[key] = data
                return_data = self.cache[key]
        else:
            return_data = self.cache[key]
            self.found[self.name] += 1
        return return_data
    
    @classmethod
    def clear(cls):
        print('Clearing cache')
        cls.cache.clear()
        for i in cls.found:
            cls.found[i] = 0

    @classmethod
    def size(cls):
        return len(cls.cache)

    @classmethod
    def extract(cls):
        return copy.deepcopy(cls.cache)

    @classmethod
    def apply(cls, cache_in):
        # We need to loop to keep the reference to cache
        for i in cache_in:
            cls.cache[i] = cache_in[i]

    @classmethod
    def values_found(cls):
        return sum(cls.found.values())

    @classmethod
    def info(cls):
        print('Caching')
        print('Number of items cached: {}'.format(cls.size()))
        print('Number of items retrieved: {}'.format(cls.found))
        print('Keys:')
        for key in cls.cache.keys():
            print('   - {}'.format(key))
