from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, hash_password, verify_password
from app.models import Company
from app.schemas import CompanyRegister, LoginRequest, TokenResponse


def register_company(payload: CompanyRegister, db: Session) -> TokenResponse:
    existing = db.query(Company).filter(Company.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company email already exists")

    company = Company(email=payload.email, password_hash=hash_password(payload.password))
    db.add(company)
    db.commit()
    db.refresh(company)
    token = create_access_token(company.id, role="company")
    return TokenResponse(access_token=token)


def login_company(payload: LoginRequest, db: Session) -> TokenResponse:
    company = db.query(Company).filter(Company.email == payload.email).first()
    if not company or not verify_password(payload.password, company.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(company.id, role="company")
    return TokenResponse(access_token=token)
