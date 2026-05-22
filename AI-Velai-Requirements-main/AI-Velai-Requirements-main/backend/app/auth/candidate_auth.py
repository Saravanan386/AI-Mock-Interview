from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, hash_password, verify_password
from app.models import Candidate
from app.schemas import CandidateRegister, LoginRequest, TokenResponse


def register_candidate(payload: CandidateRegister, db: Session) -> TokenResponse:
    existing = db.query(Candidate).filter(Candidate.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate email already exists")

    candidate = Candidate(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    token = create_access_token(candidate.id, role="candidate")
    return TokenResponse(access_token=token)


def login_candidate(payload: LoginRequest, db: Session) -> TokenResponse:
    candidate = db.query(Candidate).filter(Candidate.email == payload.email).first()
    if not candidate or not verify_password(payload.password, candidate.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(candidate.id, role="candidate")
    return TokenResponse(access_token=token)
