from sqlalchemy.orm import Session

from app.models import Company, CompanyProfile
from app.schemas import CompanyProfileUpsert


def get_profile(company: Company, db: Session) -> CompanyProfile | None:
    return db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()


def upsert_profile(company: Company, payload: CompanyProfileUpsert, db: Session) -> CompanyProfile:
    profile = get_profile(company, db)
    if profile is None:
        profile = CompanyProfile(company_id=company.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
