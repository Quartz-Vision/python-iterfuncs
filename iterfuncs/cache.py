import weakref
from collections.abc import Awaitable
from functools import wraps
from time import time
from typing import Any, Callable

from iterfuncs.typing import DecoratorFactoryT, IdT, MethodT


def make_hash(*args, **kwargs):
    """
    Generates hash from args and kwargs.
    """
    return hash(
        (args, tuple(v for _, v in sorted(kwargs.items(), key=lambda item: item[0])))
    )


def ttl_cache[
    **P, T
](ttl: int = 3600, key: Callable[..., int] = make_hash, size: int = -1,) -> IdT:
    """
    Creates a function with time-limited cache.
    TTL is specified in seconds.

    :param ttl: time to live in seconds
    :param key: function that generates cache key. By default, it uses make_hash
    :param size: maximum number of items in cache. If -1, cache is unlimited
    """

    def ttl_decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache = {}
        old_cache_version = 0

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal cache, old_cache_version

            cache_version = (
                time() // ttl
            )  # in fact, separate time in chunks of ttl and use the chunk number as version

            if old_cache_version != cache_version:
                del cache
                cache = {}
                old_cache_version = cache_version

            cache_key = key(*args, **kwargs)
            if cache_key in cache:
                return cache[cache_key]

            if size > 0 and len(cache) >= size:
                item = next(iter(cache))
                del cache[item]

            tmp = func(*args, **kwargs)
            cache[cache_key] = tmp

            return tmp

        return wrapper

    return ttl_decorator


def async_cache_adapter[
    **P, **DP, DT
](
    cache_decorator_factory: DecoratorFactoryT[
        P, Callable[DP, Callable[[], Awaitable[DT]]]
    ]
) -> DecoratorFactoryT[P, Callable[DP, Awaitable[DT]]]:
    """
    Should be used only for async functions. Every time it will return a !new! coroutine that returns cached value,
        so it should not be used inside other adapters that provide additional cache capabilities.

    Example:
        ```
        @async_cache_adapter(ttl_cache)(ttl=3600)
        async def f(x):
            return x
        ```
    """
    nothing = object()

    def transformed_decorator_factory(*d_args: P.args, **d_kwargs: P.kwargs):
        def decorator(func: Callable[DP, Awaitable]):
            @cache_decorator_factory(*d_args, **d_kwargs)
            def update_coro(*args, **kwargs):
                data: Any = nothing

                async def get_coro() -> DT:
                    nonlocal data
                    if data is nothing:
                        data = await func(*args, **kwargs)
                    return data

                return get_coro

            @wraps(func)
            async def wrapped_func(*args: DP.args, **kwargs: DP.kwargs):
                return await update_coro(*args, **kwargs)()

            return wrapped_func

        return decorator

    return transformed_decorator_factory


def method_cache_adapter[
    **P, **DP, DT
](cache_decorator_factory: DecoratorFactoryT[P, MethodT[DP, DT]]) -> DecoratorFactoryT[
    P, MethodT[DP, DT]
]:
    """
    Should be used only for instance methods and be the top level adapter (wrap all other adapters),
    so it can prevent them from handling `self`

    Example:
        ```
        class A:
            @method_cache_adapter(ttl_cache)(ttl=3600)
            def f(self, x):
                return x

        class B:
            @method_cache_adapter(async_cache_adapter(ttl_cache))(ttl=3600)
            async def f(self, x):
                return x
        ```
    """

    def transformed_decorator_factory(*d_args: P.args, **d_kwargs: P.kwargs):
        def decorator(func: MethodT[DP, DT]):
            @wraps(func)
            def wrapped_method(self, *args: DP.args, **kwargs: DP.kwargs) -> DT:
                # If we had a strong reference to self the instance would never die
                self_weak = weakref.ref(self)

                @wraps(func)
                @cache_decorator_factory(*d_args, **d_kwargs)
                def cached_method(_, *args, **kwargs):
                    return func(self_weak(), *args, **kwargs)

                # Replace the method with the cached one, so it
                # will be called next time without cache initialization
                setattr(self, func.__name__, cached_method)

                return cached_method(None, *args, **kwargs)

            return wrapped_method

        return decorator

    return transformed_decorator_factory


def amethod_cache_adapter(cache_decorator_factory):
    return method_cache_adapter(async_cache_adapter(cache_decorator_factory))
