import asyncio
import inspect
import itertools
import typing as t
from asyncio import Task
from functools import partial

import factory as fb
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .types import AsyncFactory


class AsyncSQLAlchemyOptions(fb.base.FactoryOptions):
    def _build_default_options(self) -> t.Iterable[fb.base.FactoryOptions]:
        yield from super()._build_default_options()  # type: ignore[misc]
        yield fb.base.OptionDefault("sqlalchemy_session", None, inherit=True)
        yield fb.base.OptionDefault("samaphore", None, inherit=False)


class AsyncSQLAlchemyModelFactory[T](fb.Factory):
    """Factory for SQLAlchemy models."""

    _options_class = AsyncSQLAlchemyOptions
    _original_params = None

    class Meta:
        abstract = True

    @classmethod
    def _generate(cls, strategy: t.Any, params: dict[str, t.Any]) -> T:
        cls._original_params = params
        return super()._generate(strategy, params)

    @classmethod
    def _create(cls, model_class: type[T], *args: t.Any, **kwargs: t.Any) -> Task[T]:
        """Create an instance of the model, and save it to the database."""
        session = cls._meta.sqlalchemy_session  # type: ignore[attr-defined]

        if session is None:
            raise RuntimeError("No session provided.")

        async def maker_coroutine() -> T:
            for key, value in kwargs.items():
                if inspect.isawaitable(value):
                    kwargs[key] = await value

            return await cls._save(model_class, session, args, kwargs)

        return asyncio.create_task(maker_coroutine())

    @classmethod
    async def _save(
        cls,
        model_class: type[T],
        session: AsyncSession,
        args: t.Sequence[t.Any],
        kwargs: t.Mapping[str, t.Any],
    ) -> T:
        entity = model_class(*args, **kwargs)

        session.add(entity)
        async with cls._meta.samaphore:  # type: ignore[attr-defined]
            await session.flush([entity])
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
        make_async_sqlalchemy_factory: t.Callable[[type[fb.Factory]], AsyncFactory[T]],
        session: AsyncSession,
        semaphore: asyncio.Semaphore,
    ) -> type[t.Self]:
        if name_override:
            class_name = name_override

        base_meta = fb.base.resolve_attribute("_meta", reversed(bases))

        # copy the base meta, but replace the sqlalchemy session
        meta_fields_to_copy = ("model", "exclude", "rename")

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
        all_parent_factories = itertools.chain.from_iterable(
            reversed(fb.base.get_factory_bases(base.__mro__))
            for base in reversed(fb.base.get_factory_bases(bases))
        )
        for parent_factory in all_parent_factories:
            for attr, value in vars(parent_factory).items():
                if isinstance(value, fb.declarations.SubFactory):
                    vanilla_factory = value.get_factory()
                    assert hasattr(vanilla_factory._meta, "model")
                    model = vanilla_factory._meta.model

                    if issubclass(model, DeclarativeBase):
                        sub_factory = make_async_sqlalchemy_factory(vanilla_factory)
                        defaults = (
                            value._defaults if hasattr(value, "_defaults") else {}
                        )
                        attrs[attr] = fb.SubFactory(
                            t.cast(type[fb.Factory], sub_factory), **defaults
                        )
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
        make_async_sqlalchemy_factory=partial(
            make_async_sqlalchemy_factory,
            session=session,
            cache=cache,
            semaphore=semaphore,
        ),
        semaphore=semaphore,
        session=session,
    ): ...

    cache[base_factory] = t.cast(AsyncFactory[T], AsyncSqlAlchemyFactory)

    return t.cast(AsyncFactory[T], AsyncSqlAlchemyFactory)
