import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.chatbot import assessment as assessment_service
from app.database.postgres import Base
from app.hiring.workflow import (
    create_application,
    list_candidate_interviews,
    schedule_company_interview,
    update_application_status,
    update_company_interview,
)
from app.mock_interviews import service as mock_service
from app.models import Candidate, Company, CompanyProfile, Job, Question
from app.schemas import (
    ApplicationStatusUpdate,
    AssessmentAnswer,
    AssessmentFinish,
    AssessmentStart,
    CompanyInterviewCreate,
    CompanyInterviewUpdate,
    EvaluateAnswerResponse,
    GeneratedQuestion,
    JobApplicationCreate,
    MockInterviewAnswerRequest,
    MockInterviewFinish,
    MockInterviewStart,
)


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
    company = Company(email="hiring@example.com", password_hash="hash")
    candidate = Candidate(email="ai@example.com", full_name="AI Candidate", password_hash="hash")
    db.add_all([company, candidate])
    db.flush()
    db.add(CompanyProfile(company_id=company.id, name="AI Labs"))
    source_job = Job(
        company_id=company.id,
        title="AI Engineer",
        seniority="Mid",
        skills="Python, LLM, Machine Learning",
        simple_input="Build AI products",
        generated_description="Build production AI products using Python and LLMs.",
    )
    referred_job = Job(
        company_id=company.id,
        title="LLM Engineer",
        seniority="Mid",
        skills="Python, LLM, RAG",
        simple_input="Build LLM systems",
        generated_description="Build reliable LLM and RAG systems.",
    )
    db.add_all([source_job, referred_job])
    db.flush()
    for position in range(1, 3):
        db.add(
            Question(
                job_id=source_job.id,
                text=f"Explain AI engineering scenario number {position} with a measurable result.",
                competency="AI engineering",
                difficulty="medium",
                expected_signal="specific reasoning and measurable impact",
                position=position,
            )
        )
    db.commit()
    return company, candidate, source_job, referred_job


def _complete_assessment(db, candidate, source_job, monkeypatch):
    async def evaluate(*_args, **_kwargs):
        return EvaluateAnswerResponse(score=85, feedback="Strong technical evidence.")

    monkeypatch.setattr(assessment_service, "evaluate_answer", evaluate)
    started = assessment_service.start_assessment(AssessmentStart(job_id=source_job.id), candidate, db)
    question = started.first_question
    while question:
        response = asyncio.run(
            assessment_service.answer_question(
                AssessmentAnswer(
                    assessment_id=started.assessment_id,
                    question_id=question.id,
                    answer_text="I used Python and LLM evaluation, measured quality, and improved it by 25 percent.",
                ),
                candidate,
                db,
            )
        )
        question = response.next_question
    assessment_service.finish_assessment(AssessmentFinish(assessment_id=started.assessment_id), candidate, db)
    return started.assessment_id


def test_assessment_mock_referral_application_and_company_interview(db, monkeypatch):
    company, candidate, source_job, referred_job = _seed(db)
    assessment_id = _complete_assessment(db, candidate, source_job, monkeypatch)

    async def generate_questions(*_args, **_kwargs):
        return [
            GeneratedQuestion(
                text=f"Mock interview question {number}: explain your approach and outcome.",
                competency="communication",
                difficulty="medium",
                expected_signal="clear reasoning, evidence, and measurable result",
            )
            for number in range(1, 4)
        ]

    async def evaluate_mock(*_args, **_kwargs):
        return EvaluateAnswerResponse(score=75, feedback="Clear spoken answer with relevant evidence.")

    monkeypatch.setattr(mock_service, "generate_mock_interview_questions", generate_questions)
    monkeypatch.setattr(mock_service, "evaluate_answer", evaluate_mock)
    started = asyncio.run(
        mock_service.start_mock_interview(MockInterviewStart(job_id=source_job.id, question_count=3), candidate, db)
    )
    question = started.first_question
    while question:
        response = asyncio.run(
            mock_service.answer_mock_interview(
                MockInterviewAnswerRequest(
                    mock_interview_id=started.mock_interview_id,
                    question_id=question.id,
                    answer_text="I clarified the goal, compared options, communicated tradeoffs, and measured the outcome.",
                ),
                candidate,
                db,
            )
        )
        question = response.next_question

    result = mock_service.finish_mock_interview(
        MockInterviewFinish(mock_interview_id=started.mock_interview_id, assessment_id=assessment_id),
        candidate,
        db,
    )
    assert result.career_score is not None
    assert result.career_score.assessment_score == 85
    assert result.career_score.mock_interview_score == 75
    assert result.career_score.combined_score == 81
    assert referred_job.id in {job.job_id for job in result.recommended_jobs}

    application = create_application(
        JobApplicationCreate(
            job_id=referred_job.id,
            assessment_id=assessment_id,
            mock_interview_id=started.mock_interview_id,
        ),
        candidate,
        db,
    )
    assert application.status == "applied"
    assert application.combined_score == 81

    application = update_application_status(
        application.id,
        ApplicationStatusUpdate(status="shortlisted"),
        company,
        db,
    )
    assert application.status == "shortlisted"

    scheduled = schedule_company_interview(
        CompanyInterviewCreate(
            application_id=application.id,
            round_name="Technical Round",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
            meeting_url="https://meet.example.com/technical",
        ),
        company,
        db,
    )
    assert scheduled.status == "scheduled"
    assert list_candidate_interviews(candidate, db)[0].id == scheduled.id

    completed = update_company_interview(
        scheduled.id,
        CompanyInterviewUpdate(status="completed", feedback="Strong interview performance."),
        company,
        db,
    )
    assert completed.status == "completed"
