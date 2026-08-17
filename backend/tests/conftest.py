import os
os.environ["DATABASE_URL"] = "sqlite:///./test_vtab.db"
os.environ["SECRET_KEY"] = "test-secret"
import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine
from app.main import app
from app.seed import run

@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    run()
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def token(client):
    response = client.post("/api/v1/auth/token", data={"username":"admin@vtab.local","password":"Admin123!"})
    return response.json()["access_token"]
