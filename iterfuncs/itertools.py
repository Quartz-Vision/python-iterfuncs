import asyncio
from types import EllipsisType
from typing import AsyncIterator, AsyncIterable, Awaitable, Callable, Concatenate, Iterable, Iterator, Literal, overload

from .asyncio import awaitable


async def aenumerate[T](iter: AsyncIterable[T], start=0) -> AsyncIterator[tuple[int, T]]:
    i = start
    async for elem in iter:
        yield i, elem
        i += 1


async def anext[T](iterator: AsyncIterator[T], default: T | EllipsisType = ...) -> T:
    try:
        return await iterator.__anext__()
    except StopAsyncIteration as e:
        if isinstance(default, EllipsisType):
            raise e
        return default


async def aunique[T](iter: AsyncIterable[T]) -> AsyncIterator[T]:
    seen = set()
    async for elem in iter:
        if elem not in seen:
            seen.add(elem)
            yield elem


def batched[T](values: Iterable[T], batch_size=1, rest=True) -> Iterator[list[T]]:
    batch = []
    for val in values:
        batch.append(val)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch and rest:
        yield batch


async def abatched[T](values: AsyncIterable[T], batch_size=1, rest=True) -> AsyncIterator[list[T]]:
    batch = []
    async for val in values:
        batch.append(val)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch and rest:
        yield batch




@overload
async def atuple[T1, T2](v1: Awaitable[T1] | T1, v2: Awaitable[T2] | T2, /) -> tuple[T1, T2]:
    ...


@overload
async def atuple[T1, T2, T3](v1: Awaitable[T1] | T1, v2: Awaitable[T2] | T2, v3: Awaitable[T3] | T3, /) -> tuple[T1, T2, T3]:
    ...


@overload
async def atuple[T](*values: Awaitable[T] | T) -> tuple[T, ...]:
    ...


async def atuple(*values):
    """
    Helps to gather async results, adding some not-async data to them.
    Convenient in situations, where something like async lambda would be great.
    """

    return (
        tuple(await asyncio.gather(*[awaitable(value) for value in values])) if values
        else tuple()
    )


class __Empty:
    pass


async def as_completed_gather[T](coroutines: Iterable[Awaitable[T]], batch_size=8) -> AsyncIterator[T]:
    """
    Runs coroutines in batches. It yields results in the order of the coroutines' received,
    but also tries to do it in order of their completion.
    So you have a CHANCE to move to the next iteration until the next coroutines are completed,
    unlike in `asyncio.gather`
    """

    empty = __Empty()  # it's safer to define it here to avoid any possible collisions with user's data
    empty_data: list[T | __Empty] = [empty for _ in range(batch_size)]

    for batch in batched(coroutines, batch_size):
        # we need this to have 'slots' for results so we can recieve them in a random order and store
        # them until we have some more results that we can yield in the right order
        data = empty_data.copy()
        yield_i = 0
        for real_i, random_coro in enumerate(
            asyncio.as_completed([atuple(n, coro) for n, coro in enumerate(batch)])
        ):
            coro_i, value = await random_coro
            data[coro_i] = value

            # try to yield results in order after the previous yielded until ther is a gap in the sequence (empty result)
            # if there is a gap, it means that some coroutines are not completed yet and we should try to wait for them again
            for i in range(yield_i, real_i + 1):
                if data[i] is not empty:
                    yield_i += 1
                    yield data[i]  # type: ignore
                else:
                    break
