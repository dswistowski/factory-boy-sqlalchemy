import typing as t

import factory as fb

type AsyncFactoryMaker[T] = t.Callable[[type[fb.Factory]], AsyncFactory[T]]


class AsyncFactory[Entity](t.Protocol):
    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Awaitable[Entity]: ...

    def create(self, *args: t.Any, **kwargs: t.Any) -> t.Awaitable[Entity]: ...

    def build(self, *args: t.Any, **kwargs: t.Any) -> Entity: ...

    def create_batch(
        self, n: int, *args: t.Any, **kwargs: t.Any
    ) -> list[t.Awaitable[Entity]]: ...


type Factory[Entity] = t.Callable[..., Entity]
