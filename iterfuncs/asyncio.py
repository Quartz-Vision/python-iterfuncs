import asyncio
import concurrent.futures
from functools import wraps
from typing import Any, Awaitable, Callable, Generator

type FutureLike[T] = asyncio.Future[T] | Generator[Any, None, T] | Awaitable[T]


def get_loop() -> asyncio.AbstractEventLoop:
    """
    Get current running loop or create a new one.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def as_async[**P, T](func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    """
    Decorator to make sync function async.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        loop = get_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


def as_sync[**P, T](func: Callable[P, Awaitable[T]]) -> Callable[P, T]:
    """
    Decorator to make async function sync.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return get_loop().run_until_complete(func(*args, **kwargs))

    return wrapper


def run_in_loop_background[
    T
](
    coro: FutureLike[T], loop: asyncio.AbstractEventLoop | None = None
) -> concurrent.futures.Future[T]:
    """
    Run coroutine in the background of the current loop (create a new one if none) and return future.
    """
    return asyncio.run_coroutine_threadsafe(coro, loop or get_loop())


async def awaitable[T](value: T | Awaitable[T]) -> T:
    """
    Transorm any value to awaitable.
    """
    if isinstance(value, Awaitable):
        return await value
    return value
