from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_company
from app.company.company_profile import get_profile, upsert_profile
from app.company.dashboard import company_dashboard
from app.database.postgres import get_db
from app.models import Company
from app.schemas import CompanyDashboardOut, CompanyProfileOut, CompanyProfileUpsert

router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/profile", response_model=CompanyProfileOut)
def read_company_profile(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> CompanyProfileOut:
    profile = get_profile(company, db)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company profile not found")
    return profile


@router.put("/profile", response_model=CompanyProfileOut)
def update_company_profile(
    payload: CompanyProfileUpsert,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> CompanyProfileOut:
    return upsert_profile(company, payload, db)


@router.get("/dashboard", response_model=CompanyDashboardOut)
def dashboard(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
) -> CompanyDashboardOut:
    return company_dashboard(company, db)
