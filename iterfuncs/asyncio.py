import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, Generator
import concurrent.futures


type FutureLike[T] = asyncio.Future[T] | Generator[Any, None, T] | Awaitable[T]


def get_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def as_async[**P, T](func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        loop = get_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


def run_in_loop_background[T](coro: FutureLike[T], loop: asyncio.AbstractEventLoop | None = None) -> concurrent.futures.Future[T]:
    return asyncio.run_coroutine_threadsafe(coro, loop or get_loop())


async def awaitable[T](value: T | Awaitable[T]) -> T:
    if isinstance(value, Awaitable):
        return await value
    return value

