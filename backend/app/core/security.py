from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, organization_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "role": role, "organization_id": organization_id, "exp": expires}, settings.secret_key, algorithm=ALGORITHM)


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models import DimUser
    from sqlalchemy import text
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role", "viewer")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    
    # Inject RLS session variables
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)").bindparams(uid=user_id))
    db.execute(text("SELECT set_config('app.current_role', :role, true)").bindparams(role=role))
    
    user = db.scalar(select(DimUser).where(DimUser.id == user_id, DimUser.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    def checker(user=Depends(current_user)):
        if user.role_name not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return checker

