from sqlalchemy.orm import Session

from app.jobs.job_service import create_job_with_ai
from app.models import Company, Job
from app.schemas import JobCreate


async def create_job(payload: JobCreate, company: Company, db: Session) -> Job:
    return await create_job_with_ai(payload, company, db)
