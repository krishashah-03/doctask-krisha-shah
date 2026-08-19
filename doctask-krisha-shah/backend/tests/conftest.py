import os
import shutil
from pathlib import Path

os.environ.setdefault("LLM_PROVIDER", "mock")

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Document, InjectionFlag, Pile
from app.db.session import SessionLocal, engine


@pytest.fixture()
def db_session():
    """A DB session bound to a connection whose outer transaction is rolled
    back at teardown, so tests never leave rows behind in the real database
    even though the code under test calls db.commit() internally.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def test_pile(db_session):
    """A pile scoped to one test, with its on-disk storage dir cleaned up
    afterward (the DB row itself is discarded by db_session's rollback).
    """
    pile = Pile(name="extraction-test-pile", domain="vendor_contracts")
    db_session.add(pile)
    db_session.commit()
    db_session.refresh(pile)

    yield pile

    shutil.rmtree(Path(settings.STORAGE_ROOT) / "piles" / str(pile.id), ignore_errors=True)


@pytest.fixture()
def real_pile():
    """A pile that is REALLY committed (not rolled back), for tests that
    exercise the LangGraph pipeline: graph nodes open their own independent
    DB sessions, so they can't see rows held only in db_session's
    uncommitted-to-other-connections savepoint transaction.

    Cleans up afterward: only injection_flags needs an explicit delete
    first (it references documents.id without ON DELETE CASCADE) — every
    other table cascades from piles.id, so deleting the pile handles the
    rest.
    """
    session = SessionLocal()
    pile = Pile(name="resumability-test-pile", domain="vendor_contracts")
    session.add(pile)
    session.commit()
    session.refresh(pile)

    yield pile

    document_ids = [
        row.id for row in session.query(Document.id).filter(Document.pile_id == pile.id).all()
    ]
    if document_ids:
        session.query(InjectionFlag).filter(InjectionFlag.document_id.in_(document_ids)).delete(
            synchronize_session=False
        )
        session.commit()

    pile_id = pile.id
    session.query(Pile).filter(Pile.id == pile_id).delete(synchronize_session=False)
    session.commit()
    session.close()

    shutil.rmtree(Path(settings.STORAGE_ROOT) / "piles" / str(pile_id), ignore_errors=True)
