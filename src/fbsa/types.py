import typing as t

Entity = t.TypeVar("Entity")


class AsyncFactory(t.Protocol[Entity]):
    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Awaitable[Entity]: ...

    def create(self, *args: t.Any, **kwargs: t.Any) -> t.Awaitable[Entity]: ...

    def build(self, *args: t.Any, **kwargs: t.Any) -> Entity: ...

    def create_batch(
        self, n: int, *args: t.Any, **kwargs: t.Any
    ) -> list[t.Awaitable[Entity]]: ...


Factory = t.Callable[..., Entity]
