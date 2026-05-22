from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.ai.answer_evaluator import evaluate_answer
from app.chatbot.conversation import get_next_question
from app.models import Answer, Assessment, Candidate, Job, Question, Report, Score
from app.schemas import (
    AssessmentAnswer,
    AssessmentAnswerResponse,
    AssessmentFinish,
    AssessmentResult,
    AssessmentStart,
    AssessmentStartResponse,
)
from app.scoring.report_generator import generate_report_summary
from app.scoring.scoring_service import calculate_overall_score, recommendation_for


def start_assessment(payload: AssessmentStart, candidate: Candidate, db: Session) -> AssessmentStartResponse:
    job = (
        db.query(Job)
        .options(selectinload(Job.questions))
        .filter(Job.id == payload.job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not open for assessment")
    if not job.questions:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job has no questions")

    existing = (
        db.query(Assessment)
        .options(selectinload(Assessment.answers))
        .filter(Assessment.candidate_id == candidate.id)
        .filter(Assessment.job_id == job.id)
        .filter(Assessment.status == "in_progress")
        .order_by(Assessment.started_at.desc())
        .first()
    )
    questions = sorted(job.questions, key=lambda question: question.position)
    if existing:
        answered_ids = {answer.question_id for answer in existing.answers}
        next_question = next((question for question in questions if question.id not in answered_ids), None)
        return AssessmentStartResponse(
            assessment_id=existing.id,
            first_question=next_question,
            total_questions=len(questions),
        )

    assessment = Assessment(candidate_id=candidate.id, job_id=job.id)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return AssessmentStartResponse(
        assessment_id=assessment.id,
        first_question=questions[0],
        total_questions=len(questions),
    )


async def answer_question(
    payload: AssessmentAnswer,
    candidate: Candidate,
    db: Session,
) -> AssessmentAnswerResponse:
    assessment = _get_candidate_assessment(payload.assessment_id, candidate, db)
    if assessment.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment is already completed")

    question = db.get(Question, payload.question_id)
    if not question or question.job_id != assessment.job_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found for assessment")

    existing = (
        db.query(Answer)
        .filter(Answer.assessment_id == assessment.id)
        .filter(Answer.question_id == question.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question already answered")

    evaluation = await evaluate_answer(question.text, payload.answer_text, question.expected_signal)
    answer = Answer(
        assessment_id=assessment.id,
        question_id=question.id,
        answer_text=payload.answer_text,
        evaluation_feedback=evaluation.feedback,
        score=evaluation.score,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    db.refresh(assessment)

    next_question = get_next_question(assessment, question, db)
    return AssessmentAnswerResponse(
        answer_id=answer.id,
        score=evaluation.score,
        feedback=evaluation.feedback,
        next_question=next_question,
        completed=next_question is None,
    )


def finish_assessment(payload: AssessmentFinish, candidate: Candidate, db: Session) -> AssessmentResult:
    assessment = _get_candidate_assessment(payload.assessment_id, candidate, db)
    if assessment.status == "completed":
        return result_for_assessment(assessment.id, db)

    total_questions = db.query(Question).filter(Question.job_id == assessment.job_id).count()
    answered_questions = {answer.question_id for answer in assessment.answers}
    if len(answered_questions) != total_questions:
        remaining = total_questions - len(answered_questions)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Answer all assessment questions before finishing ({remaining} remaining)",
        )

    overall = calculate_overall_score(assessment.answers)
    recommendation = recommendation_for(overall)
    report_data = generate_report_summary(assessment.answers, overall)

    score = assessment.score or Score(assessment_id=assessment.id, overall_score=overall, recommendation=recommendation)
    score.overall_score = overall
    score.recommendation = recommendation
    db.add(score)

    report = assessment.report or Report(assessment_id=assessment.id, **report_data)
    report.summary = report_data["summary"]
    report.strengths = report_data["strengths"]
    report.gaps = report_data["gaps"]
    db.add(report)

    assessment.status = "completed"
    assessment.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(assessment)
    return result_for_assessment(assessment.id, db)


def result_for_assessment(assessment_id: str, db: Session) -> AssessmentResult:
    assessment = (
        db.query(Assessment)
        .options(
            selectinload(Assessment.score),
            selectinload(Assessment.report),
            selectinload(Assessment.answers).selectinload(Answer.question),
        )
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    overall_score = assessment.score.overall_score if assessment.score else None
    answer_results = [
        {
            "question_id": answer.question_id,
            "question": answer.question.text,
            "competency": answer.question.competency,
            "score": answer.score or 0.0,
            "feedback": answer.evaluation_feedback,
        }
        for answer in sorted(assessment.answers, key=lambda item: item.question.position)
    ]
    return AssessmentResult(
        assessment_id=assessment.id,
        status=assessment.status,
        overall_score=overall_score,
        recommendation=assessment.score.recommendation if assessment.score else None,
        summary=assessment.report.summary if assessment.report else None,
        strengths=assessment.report.strengths if assessment.report else None,
        gaps=assessment.report.gaps if assessment.report else None,
        next_step=(
            "Complete the AI mock interview for this role to unlock a combined career score and job referrals."
            if assessment.status == "completed"
            else None
        ),
        answer_results=answer_results,
        recommended_jobs=[],
    )


def _get_candidate_assessment(assessment_id: str, candidate: Candidate, db: Session) -> Assessment:
    assessment = (
        db.query(Assessment)
        .options(
            selectinload(Assessment.answers),
            selectinload(Assessment.score),
            selectinload(Assessment.report),
        )
        .filter(Assessment.id == assessment_id)
        .filter(Assessment.candidate_id == candidate.id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment
