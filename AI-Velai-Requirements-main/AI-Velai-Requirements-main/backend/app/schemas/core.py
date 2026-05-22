from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class CandidateRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CompanyProfileUpsert(BaseModel):
    name: str
    industry: str | None = None
    website: str | None = None
    description: str | None = None
    location: str | None = None


class CompanyProfileOut(CompanyProfileUpsert):
    id: str
    company_id: str

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str
    simple_input: str
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    skills: list[str] = Field(default_factory=list)


class JobOut(BaseModel):
    id: str
    company_id: str
    title: str
    department: str | None
    location: str | None
    employment_type: str | None
    seniority: str | None
    skills: str | None
    simple_input: str
    generated_description: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyDashboardOut(BaseModel):
    company_id: str
    total_jobs: int
    open_jobs: int
    total_applications: int
    shortlisted_candidates: int
    scheduled_interviews: int
    jobs: list[JobOut] = Field(default_factory=list)


class QuestionOut(BaseModel):
    id: str
    job_id: str
    text: str
    competency: str | None
    difficulty: str | None
    expected_signal: str | None
    position: int

    model_config = {"from_attributes": True}


class AssessmentQuestionOut(BaseModel):
    id: str
    text: str
    competency: str | None
    difficulty: str | None
    position: int

    model_config = {"from_attributes": True}


class JobDetail(JobOut):
    questions: list[AssessmentQuestionOut] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    text: str = Field(min_length=10)
    competency: str | None = None
    difficulty: str | None = None
    expected_signal: str | None = None


class GeneratedJobResponse(BaseModel):
    description: str


class GeneratedQuestionsResponse(BaseModel):
    questions: list[GeneratedQuestion]


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    expected_signal: str | None = None


class EvaluateAnswerResponse(BaseModel):
    score: float
    feedback: str
    needs_followup: bool = False
    followup_reason: str | None = None


class AssessmentStart(BaseModel):
    job_id: str


class AssessmentStartResponse(BaseModel):
    assessment_id: str
    first_question: AssessmentQuestionOut | None = None
    total_questions: int


class AssessmentAnswer(BaseModel):
    assessment_id: str
    question_id: str
    answer_text: str = Field(min_length=10, max_length=10000)


class AssessmentAnswerResponse(BaseModel):
    answer_id: str
    score: float
    feedback: str
    next_question: AssessmentQuestionOut | None = None
    completed: bool = False


class AssessmentFinish(BaseModel):
    assessment_id: str


class AssessmentAnswerResult(BaseModel):
    question_id: str
    question: str
    competency: str | None
    score: float
    feedback: str | None


class RecommendedJob(BaseModel):
    job_id: str
    title: str
    company_name: str | None
    location: str | None
    employment_type: str | None
    required_score: float
    match_score: float
    reason: str


class AssessmentResult(BaseModel):
    assessment_id: str
    status: str
    overall_score: float | None
    recommendation: str | None
    summary: str | None
    strengths: str | None
    gaps: str | None
    next_step: str | None = None
    answer_results: list[AssessmentAnswerResult] = Field(default_factory=list)
    recommended_jobs: list[RecommendedJob] = Field(default_factory=list)


class RolePageOut(BaseModel):
    job_id: str
    title: str
    company_name: str | None
    department: str | None
    location: str | None
    employment_type: str | None
    seniority: str | None
    skills: list[str]
    description: str
    assessment_question_count: int
    assessment_available: bool
    mock_interview_available: bool = True


class MockInterviewStart(BaseModel):
    job_id: str
    question_count: int = Field(default=5, ge=3, le=10)


class MockInterviewQuestionOut(BaseModel):
    id: str
    text: str
    competency: str | None
    difficulty: str | None
    position: int

    model_config = {"from_attributes": True}


class MockInterviewStartResponse(BaseModel):
    mock_interview_id: str
    first_question: MockInterviewQuestionOut | None
    total_questions: int


class MockInterviewAnswerRequest(BaseModel):
    mock_interview_id: str
    question_id: str
    answer_text: str = Field(min_length=10, max_length=15000)


class MockInterviewAnswerResponse(BaseModel):
    answer_id: str
    score: float
    feedback: str
    needs_followup: bool = False
    followup_reason: str | None = None
    next_question: MockInterviewQuestionOut | None
    completed: bool


class MockInterviewFinish(BaseModel):
    mock_interview_id: str
    assessment_id: str | None = None


class CareerScoreOut(BaseModel):
    assessment_score: float
    mock_interview_score: float
    combined_score: float
    recommendation: str
    referral_eligible: bool


class MockInterviewResult(BaseModel):
    mock_interview_id: str
    job_id: str
    status: str
    mock_interview_score: float | None
    career_score: CareerScoreOut | None
    answer_results: list[AssessmentAnswerResult] = Field(default_factory=list)
    recommended_jobs: list[RecommendedJob] = Field(default_factory=list)


class JobApplicationCreate(BaseModel):
    job_id: str
    assessment_id: str
    mock_interview_id: str


class JobApplicationOut(BaseModel):
    id: str
    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    company_name: str | None
    assessment_score: float
    mock_interview_score: float
    combined_score: float
    status: str
    created_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: Literal["under_review", "shortlisted", "rejected", "hired"]


class CompanyInterviewCreate(BaseModel):
    application_id: str
    round_name: str = Field(min_length=2, max_length=100)
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)
    meeting_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)


class CompanyInterviewUpdate(BaseModel):
    status: Literal["scheduled", "completed", "cancelled", "no_show"]
    feedback: str | None = Field(default=None, max_length=10000)


class CompanyInterviewOut(BaseModel):
    id: str
    application_id: str
    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    company_name: str | None
    round_name: str
    scheduled_at: datetime
    duration_minutes: int
    meeting_url: str | None
    notes: str | None
    status: str
    feedback: str | None


class CandidateInterviewOut(BaseModel):
    id: str
    application_id: str
    job_id: str
    job_title: str
    company_name: str | None
    round_name: str
    scheduled_at: datetime
    duration_minutes: int
    meeting_url: str | None
    status: str
    feedback: str | None
