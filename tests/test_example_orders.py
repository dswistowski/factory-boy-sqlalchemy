import uuid
from collections.abc import AsyncIterable
from typing import Annotated, ClassVar
from uuid import UUID

import factory as fb
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Text

from fbsa import AsyncFactory, AsyncFactoryMaker

Str255 = Annotated[str, 255]


class Base(DeclarativeBase):
    type_annotation_map: ClassVar = {Str255: sa.String(255), str: Text()}


class User(Base):
    __tablename__ = "user"

    id: Mapped[Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]]
    first_name: Mapped[Str255]
    last_name: Mapped[Str255]
    email: Mapped[Str255]
    address: Mapped[str]

    owned_organizations: Mapped[list["Organization"]] = relationship(
        back_populates="owner"
    )


class UserFactory(fb.Factory):
    first_name = fb.Faker("first_name")
    last_name = fb.Faker("last_name")
    email = fb.Faker("email")
    address: str = fb.Faker("address")

    class Meta:
        model = User


@pytest.fixture
def async_user_factory(
    sqlalchemy_async_factory: AsyncFactoryMaker[User],
) -> AsyncFactory[User]:
    return sqlalchemy_async_factory(UserFactory)


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]]
    name: Mapped[Str255]
    owner_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("user.id"),
    )
    owner: Mapped[User] = relationship(
        back_populates="owned_organizations", foreign_keys=[owner_id]
    )


class OrganizationFactory(fb.Factory):
    name = fb.Faker("name")
    owner = fb.SubFactory(UserFactory)

    class Meta:
        model = Organization


@pytest.fixture
def async_organization_factory(
    sqlalchemy_async_factory: AsyncFactoryMaker[Organization],
) -> AsyncFactory[Organization]:
    return sqlalchemy_async_factory(OrganizationFactory)


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


@pytest.mark.asyncio
async def test_can_create_organization(
    async_organization_factory: AsyncFactory[Organization],
    async_session: AsyncSession,
) -> None:
    organization = await async_organization_factory(owner__first_name="Joe")

    assert organization.id

    db_organization = await async_session.get(Organization, organization.id)
    assert db_organization
    assert db_organization.owner.first_name == "Joe"
