from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.ai.answer_evaluator import evaluate_answer
from app.ai.mock_interview_generator import generate_mock_interview_questions, generate_turn_question
from app.ai.question_planner import build_role_context
from app.jobs.recommendation_service import recommend_jobs_for_assessment
from app.models import (
    Assessment,
    Candidate,
    Job,
    MockInterview,
    MockInterviewAnswer,
    MockInterviewQuestion,
)
from app.schemas import (
    CareerScoreOut,
    MockInterviewAnswerRequest,
    MockInterviewAnswerResponse,
    MockInterviewFinish,
    MockInterviewResult,
    MockInterviewStart,
    MockInterviewStartResponse,
)
from app.scoring.scoring_service import calculate_career_score, recommendation_for


async def start_mock_interview(
    payload: MockInterviewStart,
    candidate: Candidate,
    db: Session,
) -> MockInterviewStartResponse:
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not open")

    existing = (
        db.query(MockInterview)
        .options(selectinload(MockInterview.questions))
        .filter(
            MockInterview.candidate_id == candidate.id,
            MockInterview.job_id == job.id,
            MockInterview.status == "in_progress",
        )
        .order_by(MockInterview.started_at.desc())
        .first()
    )
    if existing:
        return _start_response(existing, db)

    interview = MockInterview(candidate_id=candidate.id, job_id=job.id)
    interview.target_question_count = payload.question_count
    db.add(interview)
    db.flush()
    first_batch = await generate_mock_interview_questions(
        job.generated_description,
        count=1,
        role_title=job.title,
        skills=job.skills,
        candidate_context=f"{candidate.full_name} ({candidate.email})",
    )
    first_question = first_batch[0]
    db.add(
        MockInterviewQuestion(
            mock_interview_id=interview.id,
            text=first_question.text,
            competency=first_question.competency,
            difficulty=first_question.difficulty,
            expected_signal=first_question.expected_signal,
            position=1,
        )
    )
    db.commit()
    return _start_response(interview, db)


async def answer_mock_interview(
    payload: MockInterviewAnswerRequest,
    candidate: Candidate,
    db: Session,
) -> MockInterviewAnswerResponse:
    interview = _candidate_interview(payload.mock_interview_id, candidate, db)
    if interview.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mock interview is already completed")

    question = db.get(MockInterviewQuestion, payload.question_id)
    if not question or question.mock_interview_id != interview.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found for mock interview")
    existing = db.query(MockInterviewAnswer).filter_by(
        mock_interview_id=interview.id, question_id=question.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question already answered")

    evaluation = await evaluate_answer(question.text, payload.answer_text, question.expected_signal)
    answer = MockInterviewAnswer(
        mock_interview_id=interview.id,
        question_id=question.id,
        answer_text=payload.answer_text,
        evaluation_feedback=evaluation.feedback,
        score=evaluation.score,
    )
    db.add(answer)
    db.flush()
    context = await build_role_context(interview.job.title, interview.job.skills, interview.job.generated_description)
    answered_count = db.query(MockInterviewAnswer).filter_by(mock_interview_id=interview.id).count()
    asked_texts = {
        text
        for (text,) in db.query(MockInterviewQuestion.text).filter_by(mock_interview_id=interview.id).all()
    }
    asked_competencies = [
        competency
        for (competency,) in db.query(MockInterviewQuestion.competency).filter_by(mock_interview_id=interview.id).all()
        if competency
    ]
    next_question = None
    if answered_count < interview.target_question_count:
        generated = None
        for offset in range(3):
            generated = await generate_turn_question(
                context,
                turn_index=answered_count + offset,
                asked_texts=asked_texts,
                asked_competencies=asked_competencies,
                previous_question=question.text if evaluation.needs_followup else None,
                previous_answer=payload.answer_text if evaluation.needs_followup else None,
                feedback=evaluation.followup_reason or evaluation.feedback if evaluation.needs_followup else None,
                candidate_context=f"{interview.candidate.full_name} ({interview.candidate.email})",
            )
            if generated.text not in asked_texts:
                break
        if generated and generated.text in asked_texts:
            generated = generated.model_copy(
                update={
                    "text": f"{generated.text} Give a different example or a deeper angle.",
                }
            )
        if generated and generated.text not in asked_texts:
            db.add(
                MockInterviewQuestion(
                    mock_interview_id=interview.id,
                    text=generated.text,
                    competency=generated.competency,
                    difficulty=generated.difficulty,
                    expected_signal=generated.expected_signal,
                    position=question.position + 1,
                )
            )
            db.flush()
        next_question = _next_question(interview.id, db)
    db.commit()
    db.refresh(answer)
    return MockInterviewAnswerResponse(
        answer_id=answer.id,
        score=evaluation.score,
        feedback=evaluation.feedback,
        needs_followup=evaluation.needs_followup,
        followup_reason=evaluation.followup_reason,
        next_question=next_question,
        completed=next_question is None,
    )


def finish_mock_interview(
    payload: MockInterviewFinish,
    candidate: Candidate,
    db: Session,
) -> MockInterviewResult:
    interview = _candidate_interview(payload.mock_interview_id, candidate, db)
    if interview.status == "completed":
        return mock_interview_result(interview.id, candidate, db)

    questions = db.query(MockInterviewQuestion).filter_by(mock_interview_id=interview.id).count()
    answers = db.query(MockInterviewAnswer).filter_by(mock_interview_id=interview.id).all()
    if len(answers) != questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Answer all mock interview questions before finishing ({questions - len(answers)} remaining)",
        )

    assessment = _resolve_assessment_for_mock(payload.assessment_id, interview, candidate, db)
    if payload.assessment_id and not assessment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete the assessment for this role before finishing the mock interview",
        )
    if assessment:
        interview.assessment_id = assessment.id

    interview.overall_score = round(sum(answer.score or 0.0 for answer in answers) / len(answers), 2)
    interview.status = "completed"
    interview.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return mock_interview_result(interview.id, candidate, db)


def mock_interview_result(interview_id: str, candidate: Candidate, db: Session) -> MockInterviewResult:
    interview = (
        db.query(MockInterview)
        .options(
            selectinload(MockInterview.questions).selectinload(MockInterviewQuestion.answer),
        )
        .filter(MockInterview.id == interview_id, MockInterview.candidate_id == candidate.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock interview not found")

    career_score = None
    referrals = []
    if interview.status == "completed" and interview.overall_score is not None:
        assessment = _resolve_assessment_for_mock(interview.assessment_id, interview, candidate, db)
        if assessment and assessment.score:
            combined = calculate_career_score(assessment.score.overall_score, interview.overall_score)
            referrals = recommend_jobs_for_assessment(assessment, combined, db)
            career_score = CareerScoreOut(
                assessment_score=assessment.score.overall_score,
                mock_interview_score=interview.overall_score,
                combined_score=combined,
                recommendation=recommendation_for(combined),
                referral_eligible=bool(referrals),
            )
        else:
            career_score = CareerScoreOut(
                assessment_score=interview.overall_score,
                mock_interview_score=interview.overall_score,
                combined_score=interview.overall_score,
                recommendation=recommendation_for(interview.overall_score),
                referral_eligible=interview.overall_score >= 70,
            )

    answer_results = [
        {
            "question_id": question.id,
            "question": question.text,
            "competency": question.competency,
            "score": question.answer.score if question.answer and question.answer.score is not None else 0.0,
            "feedback": question.answer.evaluation_feedback if question.answer else None,
        }
        for question in sorted(interview.questions, key=lambda item: item.position)
        if question.answer
    ]
    return MockInterviewResult(
        mock_interview_id=interview.id,
        job_id=interview.job_id,
        status=interview.status,
        mock_interview_score=interview.overall_score,
        career_score=career_score,
        answer_results=answer_results,
        recommended_jobs=referrals,
    )


def _candidate_interview(interview_id: str, candidate: Candidate, db: Session) -> MockInterview:
    interview = db.query(MockInterview).filter_by(id=interview_id, candidate_id=candidate.id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock interview not found")
    return interview


def _start_response(interview: MockInterview, db: Session) -> MockInterviewStartResponse:
    questions = db.query(MockInterviewQuestion).filter_by(mock_interview_id=interview.id).order_by(
        MockInterviewQuestion.position
    ).all()
    answered_ids = {
        question_id
        for (question_id,) in db.query(MockInterviewAnswer.question_id).filter_by(mock_interview_id=interview.id).all()
    }
    next_question = next((question for question in questions if question.id not in answered_ids), None)
    return MockInterviewStartResponse(
        mock_interview_id=interview.id,
        first_question=next_question,
        total_questions=interview.target_question_count,
    )


def _next_question(interview_id: str, db: Session) -> MockInterviewQuestion | None:
    answered_ids = db.query(MockInterviewAnswer.question_id).filter_by(mock_interview_id=interview_id)
    return (
        db.query(MockInterviewQuestion)
        .filter(MockInterviewQuestion.mock_interview_id == interview_id)
        .filter(~MockInterviewQuestion.id.in_(answered_ids))
        .order_by(MockInterviewQuestion.position)
        .first()
    )


def _resolve_assessment_for_mock(
    assessment_id: str | None,
    interview: MockInterview,
    candidate: Candidate,
    db: Session,
) -> Assessment | None:
    candidates = []
    if assessment_id:
        candidates.append(assessment_id)

    fallback_assessment = (
        db.query(Assessment)
        .options(selectinload(Assessment.score))
        .filter(
            Assessment.candidate_id == candidate.id,
            Assessment.job_id == interview.job_id,
            Assessment.status == "completed",
        )
        .order_by(Assessment.finished_at.desc().nullslast(), Assessment.started_at.desc())
        .first()
    )
    if fallback_assessment and fallback_assessment.id not in candidates:
        candidates.append(fallback_assessment.id)

    for candidate_id in candidates:
        assessment = (
            db.query(Assessment)
            .options(selectinload(Assessment.score))
            .filter(
                Assessment.id == candidate_id,
                Assessment.candidate_id == candidate.id,
                Assessment.job_id == interview.job_id,
                Assessment.status == "completed",
            )
            .first()
        )
        if assessment and assessment.score:
            return assessment
    return fallback_assessment if fallback_assessment and fallback_assessment.score else None
