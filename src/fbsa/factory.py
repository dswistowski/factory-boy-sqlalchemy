import asyncio
import typing as t
from asyncio import Task

import factory as fb
from sqlalchemy.ext.asyncio import AsyncSession

from .types import AsyncFactory


class AsyncSQLAlchemyOptions(fb.base.FactoryOptions):
    def _build_default_options(self) -> t.Iterable[fb.base.FactoryOptions]:
        yield from super()._build_default_options()  # type: ignore[misc]
        yield fb.base.OptionDefault("sqlalchemy_session", None, inherit=True)
        yield fb.base.OptionDefault("samaphore", None, inherit=False)


class AsyncSQLAlchemyModelFactory[T](fb.Factory):
    """Factory for SQLAlchemy models."""

    _options_class = AsyncSQLAlchemyOptions

    class Meta:
        abstract = True

    @classmethod
    def create(cls, **kwargs: t.Any) -> Task[T]:
        """Build the entity graph, then persist it asynchronously."""
        entity = t.cast(T, super().create(**kwargs))
        return asyncio.create_task(cls._save(entity))

    @classmethod
    def _create(cls, model_class: type[T], *args: t.Any, **kwargs: t.Any) -> T:
        """Create an instance before factory-boy runs post-generation hooks."""
        return model_class(*args, **kwargs)

    @classmethod
    async def _save(cls, entity: T) -> T:
        session: AsyncSession | None = cls._meta.sqlalchemy_session  # type: ignore[attr-defined]

        if session is None:
            raise RuntimeError("No session provided.")

        async with cls._meta.samaphore:  # type: ignore[attr-defined]
            session.add(entity)
            await session.flush()
        return entity


class AsyncSQlAlchemyFactoryMetaClass[T](fb.base.FactoryMetaClass):
    """
    This metaclass will make sure if we are using any SubFactory,
    it will be replaced from vanilla form to SQLAlchemy form.
    """

    def __new__(
        cls,
        class_name: str,
        bases: tuple[type, ...],
        attrs: dict[str, t.Any],
        name_override: str,
        session: AsyncSession,
        semaphore: asyncio.Semaphore,
    ) -> type[t.Self]:
        if name_override:
            class_name = name_override

        base_meta = fb.base.resolve_attribute("_meta", reversed(bases))

        # copy the base meta, but replace the sqlalchemy session
        meta_fields_to_copy = ("model", "inline_args", "exclude", "rename")

        meta = type(
            "Meta",
            (),
            {
                "sqlalchemy_session": session,
                "samaphore": semaphore,
                **{
                    key: value
                    for key, value in vars(base_meta).items()
                    if key in (meta_fields_to_copy)
                },
            },
        )
        attrs["Meta"] = meta
        return super().__new__(cls, class_name, bases, attrs)


def make_async_sqlalchemy_factory[T](
    base_factory: type[fb.Factory],
    *,
    session: AsyncSession,
    cache: dict[type[fb.Factory], AsyncFactory[t.Any]],
    semaphore: asyncio.Semaphore,
) -> AsyncFactory[T]:
    """
    Takes a factory, and returns a SqlFactory bound to the given session.
    """
    if existing_factory := cache.get(base_factory):
        return existing_factory

    class AsyncSqlAlchemyFactory(
        AsyncSQLAlchemyModelFactory[T],
        base_factory,  # type: ignore[valid-type, misc]
        metaclass=AsyncSQlAlchemyFactoryMetaClass,
        name_override=f"{base_factory.__name__}AsyncSqlAlchemyFactory",
        semaphore=semaphore,
        session=session,
    ): ...

    cache[base_factory] = t.cast(AsyncFactory[T], AsyncSqlAlchemyFactory)

    return t.cast(AsyncFactory[T], AsyncSqlAlchemyFactory)
