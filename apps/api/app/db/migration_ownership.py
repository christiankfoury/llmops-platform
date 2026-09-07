"""Serialize migration owners without changing the frozen database schema."""

from contextlib import contextmanager

from sqlalchemy import text


@contextmanager
def alembic_ownership(connection):
    # Match the Java migration entrypoint's session lock for this database/schema.
    schema = connection.scalar(text("SELECT current_schema()"))
    previous_timeout = connection.scalar(text("SHOW lock_timeout"))
    connection.commit()
    acquired = False
    try:
        connection.execute(text("SET lock_timeout='5s'"))
        connection.execute(
            text("SELECT pg_advisory_lock(hashtext(current_database()), hashtext(:schema))"),
            {"schema": schema},
        )
        acquired = True
        connection.commit()
        adopted = connection.scalar(
            text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                "WHERE table_schema=:schema AND table_name='flyway_schema_history')"
            ),
            {"schema": schema},
        )
        connection.commit()
        if adopted:
            raise RuntimeError("Flyway owns this schema; Alembic migration is refused")
        yield
    finally:
        connection.rollback()
        try:
            if acquired:
                connection.execute(
                    text(
                        "SELECT pg_advisory_unlock(hashtext(current_database()), hashtext(:schema))"
                    ),
                    {"schema": schema},
                )
                connection.commit()
        finally:
            connection.execute(
                text("SELECT set_config('lock_timeout', :timeout, false)"),
                {"timeout": previous_timeout},
            )
            connection.commit()
