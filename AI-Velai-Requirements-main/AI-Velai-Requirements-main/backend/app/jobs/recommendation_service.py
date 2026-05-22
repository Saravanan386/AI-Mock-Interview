import re

from sqlalchemy.orm import Session, selectinload

from app.models import Assessment, Company, Job
from app.schemas import RecommendedJob


SENIORITY_SCORE_REQUIREMENTS = {
    "intern": 40.0,
    "internship": 40.0,
    "entry": 50.0,
    "fresher": 50.0,
    "junior": 55.0,
    "mid": 65.0,
    "mid-level": 65.0,
    "senior": 75.0,
    "lead": 82.0,
    "principal": 88.0,
}

GENERIC_JOB_TERMS = {
    "associate",
    "developer",
    "engineer",
    "engineering",
    "intern",
    "junior",
    "lead",
    "manager",
    "principal",
    "senior",
    "specialist",
}


def recommend_jobs_for_assessment(
    assessment: Assessment,
    overall_score: float,
    db: Session,
    limit: int = 5,
) -> list[RecommendedJob]:
    """Recommend open roles the assessment score qualifies for.

    The completed role supplies the candidate's demonstrated skill context. Score
    eligibility is a hard gate; skill/title similarity ranks eligible roles.
    """
    source_job = db.get(Job, assessment.job_id)
    if not source_job:
        return []

    jobs = (
        db.query(Job)
        .options(selectinload(Job.company).selectinload(Company.profile))
        .filter(Job.status == "open")
        .all()
    )
    source_terms = _job_terms(source_job)
    recommendations: list[RecommendedJob] = []

    for job in jobs:
        required_score = required_score_for(job.seniority)
        if overall_score < required_score:
            continue

        target_terms = _job_terms(job)
        overlap = len(source_terms & target_terms) / max(1, len(source_terms | target_terms))
        is_assessed_role = job.id == source_job.id
        relevance = 1.0 if is_assessed_role else overlap
        match_score = round((overall_score * 0.7) + (relevance * 30.0), 2)
        if not is_assessed_role and overlap == 0:
            continue

        company_name = job.company.profile.name if job.company and job.company.profile else None
        reason = (
            f"You scored {overall_score:.1f}, above the {required_score:.1f} benchmark for this role. "
            + ("This is the role you completed the assessment for." if is_assessed_role else "Its required skills overlap with the assessed role.")
        )
        recommendations.append(
            RecommendedJob(
                job_id=job.id,
                title=job.title,
                company_name=company_name,
                location=job.location,
                employment_type=job.employment_type,
                required_score=required_score,
                match_score=match_score,
                reason=reason,
            )
        )

    return sorted(recommendations, key=lambda item: item.match_score, reverse=True)[:limit]


def required_score_for(seniority: str | None) -> float:
    normalized = (seniority or "").strip().lower()
    for label, required in SENIORITY_SCORE_REQUIREMENTS.items():
        if label in normalized:
            return required
    return 60.0


def _job_terms(job: Job) -> set[str]:
    value = f"{job.title} {job.skills or ''}"
    return {
        term.lower()
        for term in re.findall(r"[A-Za-z0-9+#.]+", value)
        if len(term) > 1 and term.lower() not in GENERIC_JOB_TERMS
    }
