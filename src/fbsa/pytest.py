import asyncio
from functools import partial
from typing import Any, cast

import factory as fb
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from .factory import make_async_sqlalchemy_factory
from .types import AsyncFactory, AsyncFactoryMaker


@pytest.fixture
def async_factory_cache() -> dict[type[fb.Factory], AsyncFactory[Any]]:
    return {}


@pytest.fixture
def semaphore() -> asyncio.Semaphore:
    return asyncio.Semaphore()


@pytest.fixture
def sqlalchemy_async_factory[T](
    async_session: AsyncSession,
    async_factory_cache: dict[type[fb.Factory], AsyncFactory[Any]],
    semaphore: asyncio.Semaphore,
) -> AsyncFactoryMaker[T]:
    return cast(
        AsyncFactoryMaker[T],
        partial(
            make_async_sqlalchemy_factory,
            session=async_session,
            cache=async_factory_cache,
            semaphore=semaphore,
        ),
    )
