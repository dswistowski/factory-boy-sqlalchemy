# factory-boy-sqlalchemy

Utilities to use factory_boy with SQLAlchemy models without hard‑binding a session in your factory definitions. You write plain, session‑less factories and bind them to an async SQLAlchemy session at test time.

This package ships a pytest plugin that provides the `sqlalchemy_async_factory` fixture to quickly create async factories bound to your test `AsyncSession`.

Note: The plugin module to enable is `fbsa.pytest` (not `fbas.pytest`).

**Why?** Many factory_boy+SQLAlchemy integrations require putting a session on each factory’s `Meta`, which couples factories to a specific session and makes reuse harder. Here, factories stay vanilla and you opt‑in to a bound async factory per test.

## Install

```bash
pip install factory-boy-sqlalchemy
```

Requires Python 3.12+, SQLAlchemy 2.x, and factory_boy 3.x.

## Quick Start (pytest)

- Add the plugin to pytest so the `sqlalchemy_async_factory` fixture is available:
  - Option 1 (recommended): in `tests/conftest.py` add `pytest_plugins = "fbsa.pytest"`.
  - Option 2: run pytest with `-p fbsa.pytest` or set it in `pytest.ini` via `addopts = -p fbsa.pytest`.

- Provide an `async_session` fixture (type `sqlalchemy.ext.asyncio.AsyncSession`).

- Define plain factory_boy factories (no session in `Meta`).

### Minimal example

```python
# tests/test_user.py
import factory as fb
import sqlalchemy as sa
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Enable plugin-provided fixtures
pytest_plugins = "fbsa.pytest"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str]


class UserFactory(fb.Factory):
    email = fb.Faker("email")

    class Meta:
        model = User


@pytest.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncSession:
    # Create/drop tables around the session as needed
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker.begin() as session:
        yield session
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def async_user_factory(sqlalchemy_async_factory):
    # Bind our vanilla UserFactory to the async session for this test
    return sqlalchemy_async_factory(UserFactory)


@pytest.mark.asyncio
async def test_creates_user(async_user_factory, async_session: AsyncSession):
    user = await async_user_factory(email="alice@example.com")

    db_user = await async_session.get(User, user.id)
    assert db_user and db_user.email == "alice@example.com"
```

## What the plugin provides

- `sqlalchemy_async_factory`: a callable fixture. Given a vanilla `factory_boy` factory class, it returns an async‑enabled factory bound to the current `AsyncSession`.
- `async_factory_cache`: an internal per‑test cache so the same base factory maps to a single bound async factory.
- `semaphore`: an `asyncio.Semaphore` (default 1) to serialize `flush()` calls; override to control concurrency.

The plugin requires an `async_session` fixture in your tests. It does not create a database engine or session for you.

Enable it with `pytest_plugins = "fbsa.pytest"` (or `-p fbsa.pytest`). This is required to provide the `sqlalchemy_async_factory` fixture.

## SubFactory support

If your vanilla factory has `SubFactory` fields, any sub‑factory whose model is a subclass of `sqlalchemy.orm.DeclarativeBase` is automatically converted into an async SQLAlchemy‑bound factory. Overrides work through double‑underscore syntax as usual.

Example:

```python
class Organization(Base):
    __tablename__ = "organization"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    owner_id: Mapped[int] = mapped_column(sa.ForeignKey("user.id"))
    owner: Mapped[User] = sa.orm.relationship()


class OrganizationFactory(fb.Factory):
    name = fb.Faker("company")
    owner = fb.SubFactory(UserFactory)

    class Meta:
        model = Organization


@pytest.fixture
def async_org_factory(sqlalchemy_async_factory):
    return sqlalchemy_async_factory(OrganizationFactory)


@pytest.mark.asyncio
async def test_nested_overrides(async_org_factory):
    org = await async_org_factory(owner__email="boss@example.com")
    assert org.owner.email == "boss@example.com"
```

## Creating batches and concurrency

The async factory returns awaitables. `create_batch(n)` returns a list of awaitables you can await concurrently, e.g. with `asyncio.gather`.

```python
import asyncio

users = await asyncio.gather(*async_user_factory.create_batch(5))
assert len(users) == 5
```

By default, the plugin’s `semaphore` fixture limits `session.flush()` concurrency to 1 to avoid DB‑specific issues. You can override this per‑test:

```python
import asyncio

@pytest.fixture
def semaphore() -> asyncio.Semaphore:
    return asyncio.Semaphore(10)  # allow more concurrent flushes
```

## Using without pytest

You can bind a factory manually via the helper:

```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fbsa.factory import make_async_sqlalchemy_factory

async def make_user(session: AsyncSession):
    async_factory = make_async_sqlalchemy_factory(
        UserFactory,
        session=session,
        cache={},
        semaphore=asyncio.Semaphore(),
    )
    return await async_factory()
```

## Notes

- Factories must have `Meta.model` set to your SQLAlchemy model.
- Only async usage is supported at the moment. There is no `make_sync_sqlalchemy_factory` in this package.
- Plugin module name is `fbsa.pytest`; enabling it is required to use `sqlalchemy_async_factory`.
