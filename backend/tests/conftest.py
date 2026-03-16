import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def app_client():
    from main import app
    return TestClient(app)
