import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine
from app.main import app as fastapi_app
import app.models


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    return TestClient(fastapi_app)

