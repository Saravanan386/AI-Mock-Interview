from fastapi import APIRouter

from app.ai.answer_evaluator import evaluate_answer
from app.ai.job_generator import generate_job_description
from app.ai.question_generator import generate_questions
from app.schemas import (
    EvaluateAnswerRequest,
    EvaluateAnswerResponse,
    GeneratedJobResponse,
    GeneratedQuestionsResponse,
    JobCreate,
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/generate-job", response_model=GeneratedJobResponse)
async def generate_job(payload: JobCreate) -> GeneratedJobResponse:
    return GeneratedJobResponse(description=await generate_job_description(payload))


@router.post("/generate-questions", response_model=GeneratedQuestionsResponse)
async def generate_interview_questions(payload: GeneratedJobResponse) -> GeneratedQuestionsResponse:
    return GeneratedQuestionsResponse(questions=await generate_questions(payload.description))


@router.post("/evaluate-answer", response_model=EvaluateAnswerResponse)
async def evaluate_candidate_answer(payload: EvaluateAnswerRequest) -> EvaluateAnswerResponse:
    return await evaluate_answer(payload.question, payload.answer, payload.expected_signal)
