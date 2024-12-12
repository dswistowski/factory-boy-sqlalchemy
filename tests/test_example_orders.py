import uuid
from collections.abc import AsyncIterable
from typing import Annotated, ClassVar
from uuid import UUID

import factory as fb
import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Text

from fbsa import AsyncFactory, AsyncFactoryMaker

Str255 = Annotated[str, 255]


class Base(DeclarativeBase):
    type_annotation_map: ClassVar = {Str255: String(255), str: Text()}


class User(Base):
    __tablename__ = "user"

    id: Mapped[Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]]
    first_name: Mapped[Str255]
    last_name: Mapped[Str255]
    email: Mapped[Str255]
    address: Mapped[str]


class UserFactory(fb.Factory):
    first_name = fb.Faker("first_name")
    last_name = fb.Faker("last_name")
    email = fb.Faker("email")
    address: str = fb.Faker("address")

    class Meta:
        model = User


@pytest.fixture
async def async_session(async_db_engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
    session_maker = async_sessionmaker(async_db_engine, expire_on_commit=False)
    async with async_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with session_maker.begin() as session:
            yield session
    finally:
        async with async_db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def async_user_factory(
    sqlalchemy_async_factory: AsyncFactoryMaker[User],
) -> AsyncFactory[User]:
    return sqlalchemy_async_factory(UserFactory)


@pytest.mark.asyncio
async def test_can_create_user(
    async_user_factory: AsyncFactory[User], async_session: AsyncSession
) -> None:
    user = await async_user_factory(first_name="Joe")

    assert user.id

    db_user = await async_session.get(User, user.id)
    assert db_user
    assert user.email == db_user.email
    assert db_user.first_name == "Joe"
