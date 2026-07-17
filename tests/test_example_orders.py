import asyncio
import uuid
import warnings
from collections.abc import AsyncIterable
from typing import Annotated, ClassVar, cast
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


def uppercase_first_name(
    user: User, create: bool, extracted: object, **kwargs: object
) -> None:
    user.first_name = user.first_name.upper()


class PostGenerationUserFactory(UserFactory):
    uppercase_name = fb.PostGeneration(uppercase_first_name)


def reject_user(user: User, create: bool, extracted: object, **kwargs: object) -> None:
    raise ValueError("post-generation rejected user")


class RejectedUserFactory(UserFactory):
    rejection = fb.PostGeneration(reject_user)


class PositionalModel(Base):
    __tablename__ = "positional_model"

    id: Mapped[Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]]
    value: Mapped[Str255]

    def __init__(self, *args: object, **kwargs: object) -> None:
        if "value" in kwargs:
            raise TypeError("value must be passed positionally")
        if len(args) != 1:
            raise TypeError("expected exactly one positional argument")
        super().__init__(value=cast(str, args[0]), **kwargs)


class PositionalModelFactory(fb.Factory):
    value = "positional"

    class Meta:
        model = PositionalModel
        inline_args = ("value",)


class Node(Base):
    __tablename__ = "node"

    id: Mapped[Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]]
    parent_id: Mapped[UUID | None] = mapped_column(
        sa.ForeignKey("node.id"), nullable=True
    )
    parent: Mapped["Node | None"] = relationship(remote_side=lambda: Node.id)


class NodeFactory(fb.Factory):
    parent = fb.SubFactory(f"{__name__}.NodeFactory")

    class Meta:
        model = Node


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


@pytest.mark.asyncio
async def test_post_generation_receives_model_and_is_persisted(
    sqlalchemy_async_factory: AsyncFactoryMaker[User],
    async_session: AsyncSession,
) -> None:
    factory = sqlalchemy_async_factory(PostGenerationUserFactory)

    user = await factory(first_name="Joe")

    assert user.first_name == "JOE"
    db_user = await async_session.get(User, user.id)
    assert db_user
    assert db_user.first_name == "JOE"


@pytest.mark.asyncio
async def test_failed_post_generation_does_not_persist(
    sqlalchemy_async_factory: AsyncFactoryMaker[User],
    async_session: AsyncSession,
) -> None:
    factory = sqlalchemy_async_factory(RejectedUserFactory)

    with pytest.raises(ValueError, match="post-generation rejected user"):
        factory()
    await asyncio.sleep(0)

    user_count = await async_session.scalar(
        sa.select(sa.func.count()).select_from(User)
    )
    assert user_count == 0


@pytest.mark.asyncio
async def test_concurrent_batch_does_not_mutate_session_during_flush(
    async_user_factory: AsyncFactory[User],
) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        users = await asyncio.gather(*async_user_factory.create_batch(20))

    session_warnings = [
        warning
        for warning in caught
        if issubclass(warning.category, sa.exc.SAWarning)
        and "Session.add()" in str(warning.message)
    ]
    assert not session_warnings
    assert len(users) == 20


@pytest.mark.asyncio
async def test_preserves_inline_args(
    sqlalchemy_async_factory: AsyncFactoryMaker[PositionalModel],
) -> None:
    factory = sqlalchemy_async_factory(PositionalModelFactory)

    entity = await factory()

    assert entity.value == "positional"


@pytest.mark.asyncio
async def test_can_bind_recursive_subfactory(
    sqlalchemy_async_factory: AsyncFactoryMaker[Node],
) -> None:
    factory = sqlalchemy_async_factory(NodeFactory)

    node = await factory(parent=None)

    assert node.id
    assert node.parent is None
