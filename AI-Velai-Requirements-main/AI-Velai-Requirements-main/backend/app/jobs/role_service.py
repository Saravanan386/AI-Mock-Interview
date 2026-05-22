from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models import Company, Job
from app.schemas import RolePageOut


def list_role_pages(db: Session) -> list[RolePageOut]:
    jobs = (
        db.query(Job)
        .options(selectinload(Job.company).selectinload(Company.profile), selectinload(Job.questions))
        .filter(Job.status == "open")
        .order_by(Job.created_at.desc())
        .all()
    )
    return [_to_role_page(job) for job in jobs]


def get_role_page(job_id: str, db: Session) -> RolePageOut:
    job = (
        db.query(Job)
        .options(selectinload(Job.company).selectinload(Company.profile), selectinload(Job.questions))
        .filter(Job.id == job_id, Job.status == "open")
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open role not found")
    return _to_role_page(job)


def _to_role_page(job: Job) -> RolePageOut:
    company_name = job.company.profile.name if job.company and job.company.profile else None
    skills = [skill.strip() for skill in (job.skills or "").split(",") if skill.strip()]
    return RolePageOut(
        job_id=job.id,
        title=job.title,
        company_name=company_name,
        department=job.department,
        location=job.location,
        employment_type=job.employment_type,
        seniority=job.seniority,
        skills=skills,
        description=job.generated_description,
        assessment_question_count=len(job.questions),
        assessment_available=bool(job.questions),
    )
