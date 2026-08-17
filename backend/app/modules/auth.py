from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, current_user, verify_password
from app.models import DimUser

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(DimUser).where(DimUser.email == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user.id, user.role_name, user.organization_id), "token_type": "bearer"}

@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role_name, "organization_id": user.organization_id}

