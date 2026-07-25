import pytest
from flask import Flask

from models import db as database


@pytest.fixture
def db():
    test_app = Flask(__name__)
    test_app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,
    )
    database.init_app(test_app)

    with test_app.app_context():
        database.create_all()
        yield database
        database.session.remove()
        database.drop_all()
