import os

import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.mysql import MySqlContainer
from testcontainers.postgres import PostgresContainer

pytest_plugins = "fbsa.pytest"


@pytest.fixture(scope="session", params=["postgresql", "sqlite", "mysql"])
def db_dsn(request, tmp_path_factory):
    """
    If DB_DSN env variable is set, use is, if not use test container to spawn a database
    """
    if request.param == "sqlite":
        db_path = tmp_path_factory.mktemp("sqlite") / "test.db"
        yield f"sqlite+aiosqlite:///{db_path}"
    elif request.param == "postgresql":
        if os.environ.get("POSTGRES_DB_DSN"):
            yield os.environ["POSTGRES_DB_DSN"]
            return

        postgres = PostgresContainer()
        postgres.start()
        try:
            yield postgres.get_connection_url(driver="psycopg")
        finally:
            postgres.stop()
    elif request.param == "mysql":
        if os.environ.get("MYSQL_DB_DSN"):
            yield os.environ["MYSQL_DB_DSN"]
            return

        mysql = MySqlContainer()
        mysql.start()
        try:
            yield mysql._create_connection_url(
                dialect="mysql+aiomysql",
                username=mysql.username,
                password=mysql.password,
                dbname=mysql.dbname,
                port=mysql.port,
            )
        finally:
            mysql.stop()
    else:
        raise RuntimeError(f"Unsuported param {request.param}")


@pytest.fixture(scope="session")
async def async_db_engine(db_dsn: str):
    engine = create_async_engine(
        db_dsn,
        echo=False,
        poolclass=NullPool,
    )
    try:
        yield engine
    finally:
        await engine.dispose()
