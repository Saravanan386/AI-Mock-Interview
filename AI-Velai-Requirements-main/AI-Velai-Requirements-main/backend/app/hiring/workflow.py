from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.jobs.recommendation_service import recommend_jobs_for_assessment
from app.models import (
    Assessment,
    Candidate,
    Company,
    CompanyInterview,
    Job,
    JobApplication,
    MockInterview,
)
from app.schemas import (
    ApplicationStatusUpdate,
    CandidateInterviewOut,
    CompanyInterviewCreate,
    CompanyInterviewOut,
    CompanyInterviewUpdate,
    JobApplicationCreate,
    JobApplicationOut,
)
from app.scoring.scoring_service import calculate_career_score


def create_application(
    payload: JobApplicationCreate,
    candidate: Candidate,
    db: Session,
) -> JobApplicationOut:
    job = db.get(Job, payload.job_id)
    if not job or job.status != "open":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open job not found")

    assessment = (
        db.query(Assessment)
        .options(selectinload(Assessment.score))
        .filter_by(id=payload.assessment_id, candidate_id=candidate.id, status="completed")
        .first()
    )
    interview = db.query(MockInterview).filter_by(
        id=payload.mock_interview_id,
        candidate_id=candidate.id,
        assessment_id=payload.assessment_id,
        status="completed",
    ).first()
    if not assessment or not assessment.score or not interview or interview.overall_score is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A completed assessment and linked mock interview are required",
        )

    combined = calculate_career_score(assessment.score.overall_score, interview.overall_score)
    eligible_ids = {
        referral.job_id for referral in recommend_jobs_for_assessment(assessment, combined, db)
    }
    if job.id not in eligible_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Combined score or role relevance does not qualify for this job",
        )

    duplicate = db.query(JobApplication).filter_by(candidate_id=candidate.id, job_id=job.id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already applied for this job")

    application = JobApplication(
        candidate_id=candidate.id,
        job_id=job.id,
        assessment_id=assessment.id,
        mock_interview_id=interview.id,
        assessment_score=assessment.score.overall_score,
        mock_interview_score=interview.overall_score,
        combined_score=combined,
    )
    db.add(application)
    db.commit()
    return application_out(application.id, db)


def candidate_applications(candidate: Candidate, db: Session) -> list[JobApplicationOut]:
    ids = [
        item_id
        for (item_id,) in db.query(JobApplication.id)
        .filter(JobApplication.candidate_id == candidate.id)
        .order_by(JobApplication.created_at.desc())
        .all()
    ]
    return [application_out(item_id, db) for item_id in ids]


def company_applications(company: Company, db: Session) -> list[JobApplicationOut]:
    ids = [
        item_id
        for (item_id,) in db.query(JobApplication.id)
        .join(Job)
        .filter(Job.company_id == company.id)
        .order_by(JobApplication.created_at.desc())
        .all()
    ]
    return [application_out(item_id, db) for item_id in ids]


def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    company: Company,
    db: Session,
) -> JobApplicationOut:
    application = _company_application(application_id, company, db)
    if application.status in {"rejected", "hired"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application status is final")
    application.status = payload.status
    db.commit()
    return application_out(application.id, db)


def schedule_company_interview(
    payload: CompanyInterviewCreate,
    company: Company,
    db: Session,
) -> CompanyInterviewOut:
    application = _company_application(payload.application_id, company, db)
    if application.status not in {"shortlisted", "under_review", "interview_completed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application must be reviewed or shortlisted before scheduling an interview",
        )
    scheduled_at = _utc_naive(payload.scheduled_at)
    if scheduled_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Interview must be in the future")

    interview = CompanyInterview(
        application_id=application.id,
        round_name=payload.round_name,
        scheduled_at=scheduled_at,
        duration_minutes=payload.duration_minutes,
        meeting_url=payload.meeting_url,
        notes=payload.notes,
    )
    application.status = "interview_scheduled"
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return company_interview_out(interview.id, db)


def update_company_interview(
    interview_id: str,
    payload: CompanyInterviewUpdate,
    company: Company,
    db: Session,
) -> CompanyInterviewOut:
    interview = _company_interview(interview_id, company, db)
    interview.status = payload.status
    interview.feedback = payload.feedback
    if payload.status == "completed":
        interview.application.status = "interview_completed"
    elif payload.status == "cancelled":
        interview.application.status = "shortlisted"
    elif payload.status == "no_show":
        interview.application.status = "under_review"
    db.commit()
    return company_interview_out(interview.id, db)


def list_company_interviews(company: Company, db: Session) -> list[CompanyInterviewOut]:
    ids = [
        interview_id
        for (interview_id,) in db.query(CompanyInterview.id)
        .join(JobApplication)
        .join(Job)
        .filter(Job.company_id == company.id)
        .order_by(CompanyInterview.scheduled_at)
        .all()
    ]
    return [company_interview_out(interview_id, db) for interview_id in ids]


def list_candidate_interviews(candidate: Candidate, db: Session) -> list[CandidateInterviewOut]:
    ids = [
        interview_id
        for (interview_id,) in db.query(CompanyInterview.id)
        .join(JobApplication)
        .filter(JobApplication.candidate_id == candidate.id)
        .order_by(CompanyInterview.scheduled_at)
        .all()
    ]
    results: list[CandidateInterviewOut] = []
    for interview_id in ids:
        item = company_interview_out(interview_id, db)
        results.append(
            CandidateInterviewOut(
                id=item.id,
                application_id=item.application_id,
                job_id=item.job_id,
                job_title=item.job_title,
                company_name=item.company_name,
                round_name=item.round_name,
                scheduled_at=item.scheduled_at,
                duration_minutes=item.duration_minutes,
                meeting_url=item.meeting_url,
                status=item.status,
                feedback=item.feedback if item.status == "completed" else None,
            )
        )
    return results


def application_out(application_id: str, db: Session) -> JobApplicationOut:
    application = (
        db.query(JobApplication)
        .options(
            selectinload(JobApplication.candidate),
            selectinload(JobApplication.job).selectinload(Job.company).selectinload(Company.profile),
        )
        .filter(JobApplication.id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    company_name = application.job.company.profile.name if application.job.company.profile else None
    return JobApplicationOut(
        id=application.id,
        candidate_id=application.candidate_id,
        candidate_name=application.candidate.full_name,
        job_id=application.job_id,
        job_title=application.job.title,
        company_name=company_name,
        assessment_score=application.assessment_score,
        mock_interview_score=application.mock_interview_score,
        combined_score=application.combined_score,
        status=application.status,
        created_at=application.created_at,
    )


def company_interview_out(interview_id: str, db: Session) -> CompanyInterviewOut:
    interview = (
        db.query(CompanyInterview)
        .options(
            selectinload(CompanyInterview.application).selectinload(JobApplication.candidate),
            selectinload(CompanyInterview.application)
            .selectinload(JobApplication.job)
            .selectinload(Job.company)
            .selectinload(Company.profile),
        )
        .filter(CompanyInterview.id == interview_id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company interview not found")
    application = interview.application
    company_name = application.job.company.profile.name if application.job.company.profile else None
    return CompanyInterviewOut(
        id=interview.id,
        application_id=application.id,
        candidate_id=application.candidate_id,
        candidate_name=application.candidate.full_name,
        job_id=application.job_id,
        job_title=application.job.title,
        company_name=company_name,
        round_name=interview.round_name,
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        meeting_url=interview.meeting_url,
        notes=interview.notes,
        status=interview.status,
        feedback=interview.feedback,
    )


def _company_application(application_id: str, company: Company, db: Session) -> JobApplication:
    application = db.query(JobApplication).join(Job).filter(
        JobApplication.id == application_id, Job.company_id == company.id
    ).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


def _company_interview(interview_id: str, company: Company, db: Session) -> CompanyInterview:
    interview = db.query(CompanyInterview).join(JobApplication).join(Job).filter(
        CompanyInterview.id == interview_id, Job.company_id == company.id
    ).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company interview not found")
    return interview


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
