from typing import Any, Callable, Concatenate

type IdT[T] = Callable[[T], T]
type MethodT[**P, T] = Callable[Concatenate[Any, P], T]
type DecoratorFT[**P, T] = Callable[P, IdT[T]]
type AbsDecoratorFT[**P] = Callable[P, IdT]
