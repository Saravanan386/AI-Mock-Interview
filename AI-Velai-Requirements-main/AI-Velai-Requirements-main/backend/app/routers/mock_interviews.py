from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_candidate
from app.database.postgres import get_db
from app.mock_interviews.service import (
    answer_mock_interview,
    finish_mock_interview,
    mock_interview_result,
    start_mock_interview,
)
from app.models import Candidate
from app.schemas import (
    MockInterviewAnswerRequest,
    MockInterviewAnswerResponse,
    MockInterviewFinish,
    MockInterviewResult,
    MockInterviewStart,
    MockInterviewStartResponse,
)

router = APIRouter(prefix="/mock-interviews", tags=["AI Mock Interviews"])


@router.post("/start", response_model=MockInterviewStartResponse)
async def start(
    payload: MockInterviewStart,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MockInterviewStartResponse:
    return await start_mock_interview(payload, candidate, db)


@router.post("/answer", response_model=MockInterviewAnswerResponse)
async def answer(
    payload: MockInterviewAnswerRequest,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MockInterviewAnswerResponse:
    return await answer_mock_interview(payload, candidate, db)


@router.post("/finish", response_model=MockInterviewResult)
def finish(
    payload: MockInterviewFinish,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MockInterviewResult:
    return finish_mock_interview(payload, candidate, db)


@router.get("/{mock_interview_id}/result", response_model=MockInterviewResult)
def result(
    mock_interview_id: str,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MockInterviewResult:
    return mock_interview_result(mock_interview_id, candidate, db)
