from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.ai.job_generator import generate_job_description
from app.ai.question_generator import generate_questions
from app.ai.vector_store import upsert_job
from app.models import Company, Job, Question
from app.schemas import JobCreate


async def create_job_with_ai(payload: JobCreate, company: Company, db: Session) -> Job:
    generated_description = await generate_job_description(payload)
    job = Job(
        company_id=company.id,
        title=payload.title,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        seniority=payload.seniority,
        skills=", ".join(payload.skills),
        simple_input=payload.simple_input,
        generated_description=generated_description,
    )
    db.add(job)
    db.flush()

    generated_questions = await generate_questions(
        generated_description,
        role_title=payload.title,
        skills=payload.skills,
    )
    for index, generated in enumerate(generated_questions, start=1):
        db.add(
            Question(
                job_id=job.id,
                text=generated.text,
                competency=generated.competency,
                difficulty=generated.difficulty,
                expected_signal=generated.expected_signal,
                position=index,
            )
        )

    db.commit()
    db.refresh(job)
    upsert_job(job)
    return get_job(job.id, db)


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.created_at.desc()).all()


def get_job(job_id: str, db: Session) -> Job:
    job = (
        db.query(Job)
        .options(selectinload(Job.questions))
        .filter(Job.id == job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.questions.sort(key=lambda question: question.position)
    return job
