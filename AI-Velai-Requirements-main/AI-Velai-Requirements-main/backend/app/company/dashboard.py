from sqlalchemy.orm import Session

from app.models import Company, CompanyInterview, Job, JobApplication
from app.schemas import CompanyDashboardOut


def company_dashboard(company: Company, db: Session) -> CompanyDashboardOut:
    jobs = db.query(Job).filter(Job.company_id == company.id).all()
    open_jobs = [job for job in jobs if job.status == "open"]
    application_query = db.query(JobApplication).join(Job).filter(Job.company_id == company.id)
    interview_query = (
        db.query(CompanyInterview)
        .join(JobApplication)
        .join(Job)
        .filter(Job.company_id == company.id)
    )
    return CompanyDashboardOut(
        company_id=company.id,
        total_jobs=len(jobs),
        open_jobs=len(open_jobs),
        total_applications=application_query.count(),
        shortlisted_candidates=application_query.filter(
            JobApplication.status.in_(["shortlisted", "interview_scheduled", "interview_completed"])
        ).count(),
        scheduled_interviews=interview_query.filter(CompanyInterview.status == "scheduled").count(),
        jobs=jobs,
    )
