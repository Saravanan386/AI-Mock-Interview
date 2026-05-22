from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.postgres import Base, get_db
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr("app.jobs.job_service.upsert_job", lambda _job: None)
    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_all_api_groups_complete_candidate_to_hire_flow(client):
    assert client.get("/health").json() == {"status": "ok"}

    company_register = client.post(
        "/company/register",
        json={"email": "api-company@example.com", "password": "password123"},
    )
    assert company_register.status_code == 200, company_register.text
    company_token = company_register.json()["access_token"]
    company_login = client.post(
        "/company/login",
        json={"email": "api-company@example.com", "password": "password123"},
    )
    assert company_login.status_code == 200, company_login.text

    candidate_register = client.post(
        "/candidate/register",
        json={
            "email": "api-candidate@example.com",
            "full_name": "API Candidate",
            "password": "password123",
        },
    )
    assert candidate_register.status_code == 200, candidate_register.text
    candidate_token = candidate_register.json()["access_token"]
    candidate_login = client.post(
        "/candidate/login",
        json={"email": "api-candidate@example.com", "password": "password123"},
    )
    assert candidate_login.status_code == 200, candidate_login.text

    profile = client.put(
        "/company/profile",
        headers=_auth(company_token),
        json={"name": "API Labs", "industry": "Artificial Intelligence", "location": "Chennai"},
    )
    assert profile.status_code == 200, profile.text
    assert client.get("/company/profile", headers=_auth(company_token)).status_code == 200

    generated_job = client.post(
        "/ai/generate-job",
        json={
            "title": "AI Engineer",
            "simple_input": "Build production LLM applications",
            "seniority": "Mid",
            "skills": ["Python", "LLM", "RAG"],
        },
    )
    assert generated_job.status_code == 200, generated_job.text
    generated_questions = client.post(
        "/ai/generate-questions",
        json={"description": generated_job.json()["description"]},
    )
    assert generated_questions.status_code == 200, generated_questions.text
    assert len(generated_questions.json()["questions"]) == 5
    evaluated = client.post(
        "/ai/evaluate-answer",
        json={
            "question": "How did you improve an LLM system?",
            "answer": "I measured retrieval quality, changed chunking, and improved accuracy by 20 percent.",
            "expected_signal": "measurement, reasoning, and measurable impact",
        },
    )
    assert evaluated.status_code == 200, evaluated.text
    assert 0 <= evaluated.json()["score"] <= 100

    created_job = client.post(
        "/jobs/create",
        headers=_auth(company_token),
        json={
            "title": "AI Engineer",
            "simple_input": "Build and evaluate production LLM and RAG products.",
            "department": "Engineering",
            "location": "Chennai",
            "employment_type": "Full-time",
            "seniority": "Mid",
            "skills": ["Python", "LLM", "RAG"],
        },
    )
    assert created_job.status_code == 200, created_job.text
    job_id = created_job.json()["id"]
    assert len(created_job.json()["questions"]) == 5
    assert "expected_signal" not in created_job.json()["questions"][0]
    assert client.get("/jobs").status_code == 200
    assert client.get(f"/jobs/{job_id}").status_code == 200

    roles = client.get("/roles")
    assert roles.status_code == 200 and roles.json()[0]["job_id"] == job_id
    assert client.get(f"/roles/{job_id}").status_code == 200

    assessment_start = client.post(
        f"/roles/{job_id}/assessment/start",
        headers=_auth(candidate_token),
    )
    assert assessment_start.status_code == 200, assessment_start.text
    assessment_id = assessment_start.json()["assessment_id"]
    resumed_assessment = client.post(
        "/assessment/start",
        headers=_auth(candidate_token),
        json={"job_id": job_id},
    )
    assert resumed_assessment.status_code == 200
    assert resumed_assessment.json()["assessment_id"] == assessment_id
    question = assessment_start.json()["first_question"]
    while question:
        answer = client.post(
            "/assessment/answer",
            headers=_auth(candidate_token),
            json={
                "assessment_id": assessment_id,
                "question_id": question["id"],
                "answer_text": (
                    "In this example I first clarified the business context and success metrics. Because reliability "
                    "mattered, I compared three technical options and documented the tradeoffs. I implemented the "
                    "Python solution, measured the outcome, reduced failures by 25 percent, and explained the result "
                    "and follow-up actions to stakeholders."
                ),
            },
        )
        assert answer.status_code == 200, answer.text
        question = answer.json()["next_question"]

    assessment_finish = client.post(
        "/assessment/finish",
        headers=_auth(candidate_token),
        json={"assessment_id": assessment_id},
    )
    assert assessment_finish.status_code == 200, assessment_finish.text
    assert assessment_finish.json()["recommended_jobs"] == []
    assert client.get(
        f"/assessment/my-result/{assessment_id}", headers=_auth(candidate_token)
    ).status_code == 200
    assert client.get(
        f"/assessment/result/{assessment_id}", headers=_auth(company_token)
    ).status_code == 200

    mock_start = client.post(
        "/mock-interviews/start",
        headers=_auth(candidate_token),
        json={"job_id": job_id, "question_count": 3},
    )
    assert mock_start.status_code == 200, mock_start.text
    mock_id = mock_start.json()["mock_interview_id"]
    resumed_mock = client.post(
        f"/roles/{job_id}/mock-interview/start",
        headers=_auth(candidate_token),
    )
    assert resumed_mock.status_code == 200
    assert resumed_mock.json()["mock_interview_id"] == mock_id
    question = mock_start.json()["first_question"]
    while question:
        answer = client.post(
            "/mock-interviews/answer",
            headers=_auth(candidate_token),
            json={
                "mock_interview_id": mock_id,
                "question_id": question["id"],
                "answer_text": (
                    "In this example I first clarified the business context and success metrics. Because reliability "
                    "mattered, I compared three technical options and documented the tradeoffs. I implemented the "
                    "Python solution, measured the outcome, reduced failures by 25 percent, and explained the result "
                    "and follow-up actions to stakeholders."
                ),
            },
        )
        assert answer.status_code == 200, answer.text
        question = answer.json()["next_question"]

    mock_finish = client.post(
        "/mock-interviews/finish",
        headers=_auth(candidate_token),
        json={"mock_interview_id": mock_id, "assessment_id": assessment_id},
    )
    assert mock_finish.status_code == 200, mock_finish.text
    result = mock_finish.json()
    assert result["career_score"] is not None
    assert result["recommended_jobs"]
    assert client.get(
        f"/mock-interviews/{mock_id}/result", headers=_auth(candidate_token)
    ).status_code == 200

    application = client.post(
        "/applications",
        headers=_auth(candidate_token),
        json={"job_id": job_id, "assessment_id": assessment_id, "mock_interview_id": mock_id},
    )
    assert application.status_code == 200, application.text
    application_id = application.json()["id"]
    assert client.get("/applications/me", headers=_auth(candidate_token)).status_code == 200
    assert client.get("/company/applications", headers=_auth(company_token)).status_code == 200

    shortlisted = client.patch(
        f"/company/applications/{application_id}",
        headers=_auth(company_token),
        json={"status": "shortlisted"},
    )
    assert shortlisted.status_code == 200, shortlisted.text
    scheduled = client.post(
        "/company/interviews",
        headers=_auth(company_token),
        json={
            "application_id": application_id,
            "round_name": "Technical Round",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
            "meeting_url": "https://meet.example.com/api-round",
        },
    )
    assert scheduled.status_code == 200, scheduled.text
    interview_id = scheduled.json()["id"]
    assert client.get("/company/interviews", headers=_auth(company_token)).status_code == 200
    candidate_interviews = client.get("/candidate/interviews", headers=_auth(candidate_token))
    assert candidate_interviews.status_code == 200
    assert "notes" not in candidate_interviews.json()[0]

    completed = client.patch(
        f"/company/interviews/{interview_id}",
        headers=_auth(company_token),
        json={"status": "completed", "feedback": "Candidate cleared the technical round."},
    )
    assert completed.status_code == 200, completed.text
    dashboard = client.get("/company/dashboard", headers=_auth(company_token))
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_applications"] == 1
