from sqlalchemy.orm import Session

from app.models import Answer, Assessment, Question


def get_next_question(assessment: Assessment, current_question: Question, db: Session) -> Question | None:
    answered_ids = {
        question_id
        for (question_id,) in db.query(Answer.question_id).filter(Answer.assessment_id == assessment.id).all()
    }
    return (
        db.query(Question)
        .filter(Question.job_id == assessment.job_id)
        .filter(~Question.id.in_(answered_ids))
        .order_by(Question.position.asc())
        .first()
    )
