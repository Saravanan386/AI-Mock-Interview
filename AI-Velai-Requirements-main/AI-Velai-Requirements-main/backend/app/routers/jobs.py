from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_company
from app.database.postgres import get_db
from app.jobs.create_job import create_job
from app.jobs.job_service import get_job, list_jobs
from app.models import Company
from app.schemas import JobCreate, JobDetail, JobOut

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/create", response_model=JobDetail)
async def create_job_endpoint(
    payload: JobCreate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> JobDetail:
    return await create_job(payload, company, db)


@router.get("", response_model=list[JobOut])
def read_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    return list_jobs(db)


@router.get("/{job_id}", response_model=JobDetail)
def read_job(job_id: str, db: Session = Depends(get_db)) -> JobDetail:
    return get_job(job_id, db)
