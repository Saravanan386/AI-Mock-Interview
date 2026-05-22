import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped["CompanyProfile | None"] = relationship(back_populates="company")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))

    company: Mapped[Company] = relationship(back_populates="profile")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="candidate")
    mock_interviews: Mapped[list["MockInterview"]] = relationship(back_populates="candidate")
    applications: Mapped[list["JobApplication"]] = relationship(back_populates="candidate")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    seniority: Mapped[str | None] = mapped_column(String(100))
    skills: Mapped[str | None] = mapped_column(Text)
    simple_input: Mapped[str] = mapped_column(Text)
    generated_description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped[Company] = relationship(back_populates="jobs")
    questions: Mapped[list["Question"]] = relationship(back_populates="job")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="job")
    mock_interviews: Mapped[list["MockInterview"]] = relationship(back_populates="job")
    applications: Mapped[list["JobApplication"]] = relationship(back_populates="job")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    competency: Mapped[str | None] = mapped_column(String(255))
    difficulty: Mapped[str | None] = mapped_column(String(50))
    expected_signal: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0)

    job: Mapped[Job] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    candidate: Mapped[Candidate] = relationship(back_populates="assessments")
    job: Mapped[Job] = relationship(back_populates="assessments")
    answers: Mapped[list["Answer"]] = relationship(back_populates="assessment")
    score: Mapped["Score | None"] = relationship(back_populates="assessment")
    report: Mapped["Report | None"] = relationship(back_populates="assessment")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    answer_text: Mapped[str] = mapped_column(Text)
    evaluation_feedback: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assessment: Mapped[Assessment] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="answers")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), unique=True)
    overall_score: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assessment: Mapped[Assessment] = relationship(back_populates="score")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    strengths: Mapped[str | None] = mapped_column(Text)
    gaps: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assessment: Mapped[Assessment] = relationship(back_populates="report")


class MockInterview(Base):
    __tablename__ = "mock_interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id"), index=True)
    target_question_count: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    overall_score: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    candidate: Mapped[Candidate] = relationship(back_populates="mock_interviews")
    job: Mapped[Job] = relationship(back_populates="mock_interviews")
    assessment: Mapped[Assessment | None] = relationship()
    questions: Mapped[list["MockInterviewQuestion"]] = relationship(back_populates="mock_interview")
    applications: Mapped[list["JobApplication"]] = relationship(back_populates="mock_interview")


class MockInterviewQuestion(Base):
    __tablename__ = "mock_interview_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    mock_interview_id: Mapped[str] = mapped_column(ForeignKey("mock_interviews.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    competency: Mapped[str | None] = mapped_column(String(255))
    difficulty: Mapped[str | None] = mapped_column(String(50))
    expected_signal: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0)

    mock_interview: Mapped[MockInterview] = relationship(back_populates="questions")
    answer: Mapped["MockInterviewAnswer | None"] = relationship(back_populates="question")


class MockInterviewAnswer(Base):
    __tablename__ = "mock_interview_answers"
    __table_args__ = (UniqueConstraint("mock_interview_id", "question_id", name="uq_mock_answer_question"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    mock_interview_id: Mapped[str] = mapped_column(ForeignKey("mock_interviews.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("mock_interview_questions.id"), index=True)
    answer_text: Mapped[str] = mapped_column(Text)
    evaluation_feedback: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    mock_interview: Mapped[MockInterview] = relationship()
    question: Mapped[MockInterviewQuestion] = relationship(back_populates="answer")


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_application"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    mock_interview_id: Mapped[str] = mapped_column(ForeignKey("mock_interviews.id"), index=True)
    assessment_score: Mapped[float] = mapped_column(Float)
    mock_interview_score: Mapped[float] = mapped_column(Float)
    combined_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="applied")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    candidate: Mapped[Candidate] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(back_populates="applications")
    assessment: Mapped[Assessment] = relationship()
    mock_interview: Mapped[MockInterview] = relationship(back_populates="applications")
    interviews: Mapped[list["CompanyInterview"]] = relationship(back_populates="application")


class CompanyInterview(Base):
    __tablename__ = "company_interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id"), index=True)
    round_name: Mapped[str] = mapped_column(String(100))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    meeting_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped[JobApplication] = relationship(back_populates="interviews")
