import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["API_KEY"] = "ratescope-demo-key"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:19092"
os.environ["APP_ENV"] = "test"
os.environ["DEMO_MODE"] = "false"

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.db import Base, get_db
from app.main import app
from app.models.entities import ExchangeRate, Hotel, Room, Supplier
from app.seed_data import seed_reference

get_settings.cache_clear()

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    seed_reference(session)
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def _get_db():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def hotel_room(db):
    hotel = db.query(Hotel).first()
    room = db.query(Room).filter(Room.hotel_id == hotel.id).first()
    return hotel, room
