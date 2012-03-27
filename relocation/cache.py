import logging
from random import randrange
from time import time
from contextlib import contextmanager

from django.core.cache import get_cache
from django.core.cache import cache

from .dtypes import Timer

class NotFound: pass
class SkipCaching(Exception):
    pass

def compute_recache_period(options):
    return options.PERIOD + randrange(-1*options.FUZZ, options.FUZZ)

@contextmanager
def cached_data(key, backend=cache, commit_on_exception=False, recache_strategy=None):
    class CacheContext:
        response = NotFound
        found = False
        recache = False
        set_kwargs = {}

    if isinstance(backend, basestring):
        backend = get_cache(backend)
    timer = Timer()
    ctx = CacheContext()
    from_cache, recache_time = backend.get(key, (NotFound, float('inf')))
    if from_cache is not NotFound:
        ctx.response = from_cache
        if recache_strategy and recache_time < time() and backend.add(key + ':recache', 1,
                                                                      timeout=recache_strategy.TIMEOUT):
            logging.getLogger('audish.cache').debug('%s is recaching', key)
            ctx.recache = True
        else:
            ctx.found = True

    exception = False
    try:
        yield ctx
    except SkipCaching:
        ctx.found = True
    except:
        exception = True
        raise
    finally:
        if not ctx.found and (not exception or commit_on_exception):
            recache_period = compute_recache_period(recache_strategy) if recache_strategy else float('inf') 
            logging.getLogger('audish.cache').debug(
                '%s (%.1fs/%s/%d/%d)',
                key, timer.elapsed, recache_period, exception, commit_on_exception
            )
            backend.set(key, (ctx.response, time() + recache_period), **ctx.set_kwargs)
        if ctx.recache:
            backend.delete(key + ':recache')
