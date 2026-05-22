import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.chatbot import assessment as assessment_service
from app.database.postgres import Base
from app.models import Candidate, Company, CompanyProfile, Job, Question
from app.schemas import AssessmentAnswer, AssessmentFinish, AssessmentStart, EvaluateAnswerResponse


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _seed(db):
    company = Company(email="company@example.com", password_hash="hash")
    candidate = Candidate(email="candidate@example.com", full_name="Candidate", password_hash="hash")
    db.add_all([company, candidate])
    db.flush()
    db.add(CompanyProfile(company_id=company.id, name="Acme", industry="Technology"))

    assessed_job = Job(
        company_id=company.id,
        title="Python Developer",
        seniority="Junior",
        skills="Python, FastAPI",
        simple_input="Build APIs",
        generated_description="Build Python APIs",
    )
    related_job = Job(
        company_id=company.id,
        title="Backend Python Engineer",
        seniority="Junior",
        skills="Python, SQL",
        simple_input="Build services",
        generated_description="Build backend services",
    )
    unrelated_job = Job(
        company_id=company.id,
        title="Visual Designer",
        seniority="Junior",
        skills="Figma",
        simple_input="Design interfaces",
        generated_description="Design interfaces",
    )
    db.add_all([assessed_job, related_job, unrelated_job])
    db.flush()
    db.add_all(
        [
            Question(
                job_id=assessed_job.id,
                text="Explain a Python API you built and its measurable result.",
                competency="Python",
                expected_signal="specific actions and measurable impact",
                difficulty="medium",
                position=1,
            ),
            Question(
                job_id=assessed_job.id,
                text="How did you test and monitor that API in production?",
                competency="quality",
                expected_signal="testing monitoring and sound reasoning",
                difficulty="medium",
                position=2,
            ),
        ]
    )
    db.commit()
    return candidate, assessed_job


def test_complete_assessment_returns_breakdown_and_job_referrals(db, monkeypatch):
    candidate, job = _seed(db)

    async def successful_evaluation(*_args, **_kwargs):
        return EvaluateAnswerResponse(score=80, feedback="Relevant evidence and a clear result.")

    monkeypatch.setattr(assessment_service, "evaluate_answer", successful_evaluation)
    started = assessment_service.start_assessment(AssessmentStart(job_id=job.id), candidate, db)
    resumed = assessment_service.start_assessment(AssessmentStart(job_id=job.id), candidate, db)
    assert resumed.assessment_id == started.assessment_id

    first = started.first_question
    assert first is not None
    assert "expected_signal" not in first.model_dump()
    first_response = asyncio.run(
        assessment_service.answer_question(
            AssessmentAnswer(
                assessment_id=started.assessment_id,
                question_id=first.id,
                answer_text="I built the API, measured latency, and improved it by 30 percent.",
            ),
            candidate,
            db,
        )
    )
    assert first_response.score == 80
    assert first_response.next_question is not None

    with pytest.raises(HTTPException) as incomplete:
        assessment_service.finish_assessment(AssessmentFinish(assessment_id=started.assessment_id), candidate, db)
    assert incomplete.value.status_code == 409

    asyncio.run(
        assessment_service.answer_question(
            AssessmentAnswer(
                assessment_id=started.assessment_id,
                question_id=first_response.next_question.id,
                answer_text="I added integration tests and monitored errors and latency after release.",
            ),
            candidate,
            db,
        )
    )
    result = assessment_service.finish_assessment(
        AssessmentFinish(assessment_id=started.assessment_id), candidate, db
    )

    assert result.status == "completed"
    assert result.overall_score == 80
    assert result.recommendation == "hire"
    assert len(result.answer_results) == 2
    assert result.recommended_jobs == []
    assert result.next_step is not None


def test_answer_validation_rejects_too_short_text():
    with pytest.raises(ValueError):
        AssessmentAnswer(assessment_id="a", question_id="q", answer_text="short")
