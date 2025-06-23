import asyncio
from types import EllipsisType
from typing import AsyncIterable, AsyncIterator, Awaitable, Iterable, Iterator, overload

from .asyncio import awaitable


async def aenumerate[T](iter: AsyncIterable[T], start=0) -> AsyncIterator[tuple[int, T]]:
    """
    Asynchronous version of `enumerate` function.
    """
    i = start
    async for elem in iter:
        yield i, elem
        i += 1


async def anext[T](iterator: AsyncIterator[T], default: T | EllipsisType = ...) -> T:
    """
    Asynchronous version of `next` function.
    """
    try:
        return await iterator.__anext__()
    except StopAsyncIteration as e:
        if isinstance(default, EllipsisType):
            raise e
        return default


async def aunique[T](iter: AsyncIterable[T]) -> AsyncIterator[T]:
    """
    Asynchronous version of `unique_everseen` function.
    """
    seen = set()
    async for elem in iter:
        if elem not in seen:
            seen.add(elem)
            yield elem


async def aunique_justseen[T](iter: AsyncIterable[T]) -> AsyncIterator[T]:
    """
    Asynchronous version of `unique_justseen` function.
    """
    last = object()
    async for elem in iter:
        if elem != last:
            last = elem
            yield elem


def batched[T](values: Iterable[T], batch_size=1, rest=True) -> Iterator[list[T]]:
    """
    Iterator that splits values into batches.

    :param values: Iterable of values.
    :param batch_size: Size of a batch.
    :param rest: If True, the last batch will be yielded even if it's smaller than `batch_size`.
    """
    batch = []
    for val in values:
        batch.append(val)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch and rest:
        yield batch


async def abatched[
    T
](values: AsyncIterable[T], batch_size=1, rest=True) -> AsyncIterator[list[T]]:
    """
    Asynchronous version of `batched` function.
    """
    batch = []
    async for val in values:
        batch.append(val)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch and rest:
        yield batch


@overload
async def atuple[
    T1, T2
](v1: Awaitable[T1] | T1, v2: Awaitable[T2] | T2, /) -> tuple[T1, T2]: ...


@overload
async def atuple[
    T1, T2, T3
](v1: Awaitable[T1] | T1, v2: Awaitable[T2] | T2, v3: Awaitable[T3] | T3, /) -> tuple[
    T1, T2, T3
]: ...


@overload
async def atuple[T](*values: Awaitable[T] | T) -> tuple[T, ...]: ...


async def atuple(*values):
    """
    Helps to gather async results, adding some not-async data to them.
    Convenient in situations, where something like async lambda would be great.
    """

    return (
        tuple(await asyncio.gather(*[awaitable(value) for value in values]))
        if values
        else tuple()
    )


class __Empty:
    pass


async def _as_completed_limited_return_exceptions[
    T
](coroutines: Iterable[Awaitable[T]], concurrency: int) -> AsyncIterator[T | Exception]:
    """
    Returns exceptions as well as results.
    Has a slight overhead compared to `_as_completed_limited_raise_exceptions` because of try-except.
    """
    loop = asyncio.get_event_loop()
    tasks: list[asyncio.Task | None] = [None for _ in range(concurrency)]

    task_buffer_idx = 0
    for coro in coroutines:
        while True:
            task_buffer_idx = (task_buffer_idx + 1) % concurrency
            task = tasks[task_buffer_idx]
            if task is None or task.done():
                tasks[task_buffer_idx] = loop.create_task(coro)  # type: ignore
                if task is not None:
                    try:
                        yield await task
                    except Exception as e:
                        yield e
                break
            elif task_buffer_idx == concurrency - 1:
                # let the event loop run to allow other tasks to complete
                await asyncio.sleep(0)

    for task in asyncio.as_completed(t for t in tasks if t is not None):
        try:
            yield await task
        except Exception as e:
            yield e


async def _as_completed_limited_raise_exceptions[
    T
](coroutines: Iterable[Awaitable[T]], concurrency: int) -> AsyncIterator[T]:
    """
    Doesn't handle exceptions. So they will be raised.
    """
    loop = asyncio.get_event_loop()
    tasks: list[asyncio.Task | None] = [None for _ in range(concurrency)]

    task_buffer_idx = -1
    for coro in coroutines:
        while True:
            task_buffer_idx = (task_buffer_idx + 1) % concurrency
            task = tasks[task_buffer_idx]
            if task is None or task.done():
                tasks[task_buffer_idx] = loop.create_task(coro)  # type: ignore
                if task is not None:
                    yield await task
                break
            elif task_buffer_idx == concurrency - 1:
                # let the event loop run to allow other tasks to complete
                await asyncio.sleep(0)

    for task in asyncio.as_completed(t for t in tasks if t is not None):
        yield await task


def as_completed_limited[
    T
](
    coroutines: Iterable[Awaitable[T]], concurrency=8, return_exceptions=False
) -> AsyncIterator[T | Exception]:
    """
    Works like `asyncio.as_completed`, but limits the number of coroutines running at the same time.

    Args:
        coroutines: Iterable of awaitable objects to run concurrently
        concurrency: Maximum number of coroutines to run at the same time (default: 8)
        return_exceptions: If True, exceptions are returned as values instead of being raised (default: False)

    Returns:
        AsyncIterator that yields results as they complete

    Examples:
        >>> async def example():
        ...     coros = [asyncio.sleep(1), asyncio.sleep(2), asyncio.sleep(0.5)]
        ...     async for result in as_completed_limited(coros, concurrency=2):
        ...         print(result)
        >>> # Will print results as they complete, with max 2 running at once
    """
    if return_exceptions:
        return _as_completed_limited_return_exceptions(coroutines, concurrency)
    else:
        return _as_completed_limited_raise_exceptions(coroutines, concurrency)


async def _as_completed_gather_return_exceptions[
    T
](coroutines: Iterable[Awaitable[T]], batch_size: int) -> AsyncIterator[T | Exception]:
    """
    Returns exceptions as well as results.
    Has a slight overhead compared to `_as_completed_gather_raise_exceptions` because of try-except.
    """
    loop = asyncio.get_event_loop()
    tasks: list[tuple[int, asyncio.Task] | None] = [None for _ in range(batch_size)]

    task_buffer_idx = -1
    yield_idx = 0
    for coro_idx, coro in enumerate(coroutines):
        while True:
            task_buffer_idx = (task_buffer_idx + 1) % batch_size
            item = tasks[task_buffer_idx]
            if item is not None:
                task_coro_idx, task = item

                if task_coro_idx == yield_idx and task.done():
                    tasks[task_buffer_idx] = (coro_idx, loop.create_task(coro))  # type: ignore
                    yield_idx += 1
                    try:
                        yield await task
                    except Exception as e:
                        yield e
                    break
                elif task_buffer_idx == batch_size - 1:
                    await asyncio.sleep(0)
            else:
                tasks[task_buffer_idx] = (coro_idx, loop.create_task(coro))  # type: ignore
                break

    for item in sorted((t for t in tasks if t is not None), key=lambda x: x[0]):
        try:
            yield await item[1]
        except Exception as e:
            yield e


async def _as_completed_gather_raise_exceptions[
    T
](coroutines: Iterable[Awaitable[T]], batch_size: int) -> AsyncIterator[T]:
    """
    Doesn't handle exceptions. So they will be raised.
    """
    loop = asyncio.get_event_loop()
    tasks: list[tuple[int, asyncio.Task] | None] = [None for _ in range(batch_size)]

    task_buffer_idx = -1
    yield_idx = 0
    for coro_idx, coro in enumerate(coroutines):
        while True:
            task_buffer_idx = (task_buffer_idx + 1) % batch_size
            item = tasks[task_buffer_idx]
            if item is not None:
                task_coro_idx, task = item

                if task_coro_idx == yield_idx and task.done():
                    tasks[task_buffer_idx] = (coro_idx, loop.create_task(coro))  # type: ignore
                    yield_idx += 1
                    yield await task
                    break
                elif task_buffer_idx == batch_size - 1:
                    await asyncio.sleep(0)
            else:
                tasks[task_buffer_idx] = (coro_idx, loop.create_task(coro))  # type: ignore
                break

    for item in sorted((t for t in tasks if t is not None), key=lambda x: x[0]):
        yield await item[1]


def as_completed_gather[
    T
](
    coroutines: Iterable[Awaitable[T]], batch_size=8, return_exceptions=False
) -> AsyncIterator[T | Exception]:
    """
    Runs coroutines in batches. It yields results in the order of the coroutines' received,
    but also tries to do it in order of their completion.
    So you have a CHANCE to move to the next iteration until all the coroutines are completed,
    unlike in `asyncio.gather`. Uses `asyncio.as_completed` under the hood.

    Args:
        coroutines: Iterable of awaitable objects to run in batches
        batch_size: Size of each batch (default: 8)
        return_exceptions: If True, exceptions are returned as values instead of being raised (default: False)

    Returns:
        AsyncIterator that yields results as they complete

    Examples:
        >>> async def example():
        ...     coros = [asyncio.sleep(1), asyncio.sleep(2), asyncio.sleep(0.5)]
        ...     async for result in as_completed_gather(coros, batch_size=2):
        ...         print(result)
        >>> # Will print results as they complete, processing in batches of 2
    """
    if return_exceptions:
        return _as_completed_gather_return_exceptions(coroutines, batch_size)
    else:
        return _as_completed_gather_raise_exceptions(coroutines, batch_size)


async def consume[T](iter: AsyncIterable[T]):
    """
    Consumes an async iterable.
    """
    async for _ in iter:
        pass


async def consume_raise[T](iter: AsyncIterable[T]) -> AsyncIterator[Exception]:
    """
    Consumes an async iterable, raising exceptions.
    """
    while True:
        try:
            async for _ in iter:
                pass
        except Exception as e:
            yield e
        else:
            break
