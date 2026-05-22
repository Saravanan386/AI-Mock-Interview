from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.candidate_auth import login_candidate, register_candidate
from app.auth.company_auth import login_company, register_company
from app.database.postgres import get_db
from app.schemas import CandidateRegister, CompanyRegister, LoginRequest, TokenResponse

router = APIRouter(tags=["Authentication"])


@router.post("/company/register", response_model=TokenResponse)
def company_register(payload: CompanyRegister, db: Session = Depends(get_db)) -> TokenResponse:
    return register_company(payload, db)


@router.post("/company/login", response_model=TokenResponse)
def company_login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_company(payload, db)


@router.post("/candidate/register", response_model=TokenResponse)
def candidate_register(payload: CandidateRegister, db: Session = Depends(get_db)) -> TokenResponse:
    return register_candidate(payload, db)


@router.post("/candidate/login", response_model=TokenResponse)
def candidate_login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_candidate(payload, db)
