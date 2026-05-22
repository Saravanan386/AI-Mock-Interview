from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_candidate
from app.chatbot.assessment import start_assessment
from app.database.postgres import get_db
from app.jobs.role_service import get_role_page, list_role_pages
from app.mock_interviews.service import start_mock_interview
from app.models import Candidate
from app.schemas import (
    AssessmentStart,
    AssessmentStartResponse,
    MockInterviewStart,
    MockInterviewStartResponse,
    RolePageOut,
)

router = APIRouter(prefix="/roles", tags=["Role Pages"])


@router.get("", response_model=list[RolePageOut])
def roles(db: Session = Depends(get_db)) -> list[RolePageOut]:
    return list_role_pages(db)


@router.get("/{job_id}", response_model=RolePageOut)
def role(job_id: str, db: Session = Depends(get_db)) -> RolePageOut:
    return get_role_page(job_id, db)


@router.post("/{job_id}/assessment/start", response_model=AssessmentStartResponse)
def role_assessment_start(
    job_id: str,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> AssessmentStartResponse:
    return start_assessment(AssessmentStart(job_id=job_id), candidate, db)


@router.post("/{job_id}/mock-interview/start", response_model=MockInterviewStartResponse)
async def role_mock_interview_start(
    job_id: str,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MockInterviewStartResponse:
    return await start_mock_interview(MockInterviewStart(job_id=job_id), candidate, db)
