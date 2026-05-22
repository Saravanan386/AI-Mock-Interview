from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_candidate, get_current_company
from app.chatbot.assessment import answer_question, finish_assessment, result_for_assessment, start_assessment
from app.database.postgres import get_db
from app.models import Assessment, Candidate, Company, Job
from app.schemas import (
    AssessmentAnswer,
    AssessmentAnswerResponse,
    AssessmentFinish,
    AssessmentResult,
    AssessmentStart,
    AssessmentStartResponse,
)

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.post("/start", response_model=AssessmentStartResponse)
def start(
    payload: AssessmentStart,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> AssessmentStartResponse:
    return start_assessment(payload, candidate, db)


@router.post("/answer", response_model=AssessmentAnswerResponse)
async def answer(
    payload: AssessmentAnswer,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> AssessmentAnswerResponse:
    return await answer_question(payload, candidate, db)


@router.post("/finish", response_model=AssessmentResult)
def finish(
    payload: AssessmentFinish,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> AssessmentResult:
    return finish_assessment(payload, candidate, db)


@router.get("/result/{assessment_id}", response_model=AssessmentResult)
def result(
    assessment_id: str,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> AssessmentResult:
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    job = db.get(Job, assessment.job_id)
    if not job or job.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Result is not owned by this company")
    return result_for_assessment(assessment_id, db)


@router.get("/my-result/{assessment_id}", response_model=AssessmentResult)
def candidate_result(
    assessment_id: str,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> AssessmentResult:
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if assessment.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Result does not belong to this candidate")
    return result_for_assessment(assessment_id, db)
