from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_candidate, get_current_company
from app.database.postgres import get_db
from app.hiring.workflow import (
    candidate_applications,
    company_applications,
    create_application,
    list_candidate_interviews,
    list_company_interviews,
    schedule_company_interview,
    update_application_status,
    update_company_interview,
)
from app.models import Candidate, Company
from app.schemas import (
    ApplicationStatusUpdate,
    CandidateInterviewOut,
    CompanyInterviewCreate,
    CompanyInterviewOut,
    CompanyInterviewUpdate,
    JobApplicationCreate,
    JobApplicationOut,
)

router = APIRouter(tags=["Hiring Pipeline"])


@router.post("/applications", response_model=JobApplicationOut)
def apply_for_referred_job(
    payload: JobApplicationCreate,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> JobApplicationOut:
    return create_application(payload, candidate, db)


@router.get("/applications/me", response_model=list[JobApplicationOut])
def my_applications(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[JobApplicationOut]:
    return candidate_applications(candidate, db)


@router.get("/company/applications", response_model=list[JobApplicationOut])
def read_company_applications(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> list[JobApplicationOut]:
    return company_applications(company, db)


@router.patch("/company/applications/{application_id}", response_model=JobApplicationOut)
def change_application_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> JobApplicationOut:
    return update_application_status(application_id, payload, company, db)


@router.post("/company/interviews", response_model=CompanyInterviewOut)
def schedule_interview(
    payload: CompanyInterviewCreate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> CompanyInterviewOut:
    return schedule_company_interview(payload, company, db)


@router.get("/company/interviews", response_model=list[CompanyInterviewOut])
def company_interviews(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> list[CompanyInterviewOut]:
    return list_company_interviews(company, db)


@router.patch("/company/interviews/{interview_id}", response_model=CompanyInterviewOut)
def change_interview(
    interview_id: str,
    payload: CompanyInterviewUpdate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> CompanyInterviewOut:
    return update_company_interview(interview_id, payload, company, db)


@router.get("/candidate/interviews", response_model=list[CandidateInterviewOut])
def candidate_interviews(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[CandidateInterviewOut]:
    return list_candidate_interviews(candidate, db)
