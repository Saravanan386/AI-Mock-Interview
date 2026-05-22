import os

os.environ.setdefault("database_url", "sqlite:///:memory:")
os.environ.setdefault("jwt_secret_key", "test-secret")
os.environ.setdefault("jwt_algorithm", "HS256")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.candidate_auth import register_candidate
from app.auth.company_auth import register_company
from app.database.postgres import Base
from app.models import Candidate, Company
from app.schemas import CandidateRegister, CompanyRegister


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_company_registration_returns_token(db_session: Session) -> None:
    response = register_company(
        CompanyRegister(email="company@example.com", password="strongpass123"),
        db_session,
    )

    assert response.access_token
    assert db_session.query(Company).filter(Company.email == "company@example.com").count() == 1


def test_candidate_registration_returns_token(db_session: Session) -> None:
    response = register_candidate(
        CandidateRegister(email="candidate@example.com", full_name="Jane Doe", password="strongpass123"),
        db_session,
    )

    assert response.access_token
    assert db_session.query(Candidate).filter(Candidate.email == "candidate@example.com").count() == 1
