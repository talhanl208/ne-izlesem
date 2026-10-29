import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neizlesem import create_app  # noqa: E402
from tests.fakes import FakeSession  # noqa: E402


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def app(tmp_path, fake_session):
    app = create_app(
        {
            "TESTING": True,
            "TMDB_API_KEY": "test-anahtar",
            "OMDB_API_KEY": "test-omdb",
            "DATABASE_PATH": str(tmp_path / "test.db"),
            "MAX_WORKERS": 4,
        },
        session=fake_session,
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def services(app):
    return app.extensions["neizlesem"]
