from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, current_user, verify_password, hash_password, require_roles
from app.models import DimUser
from app.schemas import UserCreate, UserVerify
from app.services.email_service import send_verification_email, send_query_email
import uuid
import random
import string
import time
import pyotp
import qrcode
import io
import base64
from jose import jwt
from app.core.security import ALGORITHM
from app.core.config import settings
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

PENDING_USERS = {}

@router.post("/token")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    from sqlalchemy import text
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.is_login', 'true', true)"))
    user = db.scalar(select(DimUser).where(DimUser.email == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    if user.mfa_enabled:
        temp_token = create_access_token(user.id, user.role_name, user.organization_id)
        raise HTTPException(status_code=403, detail={"error": "mfa_required", "temp_token": temp_token})

    return {"access_token": create_access_token(user.id, user.role_name, user.organization_id), "token_type": "bearer"}

@router.post("/mfa/setup")
def mfa_setup(user = Depends(current_user), db: Session = Depends(get_db)):
    db_user = db.get(DimUser, user.id)
    secret = pyotp.random_base32()
    db_user.mfa_secret = secret
    db.commit()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=db_user.email, issuer_name="VTAB Sentinel")
    
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    return {"qr_code_b64": qr_b64, "secret": secret}

@router.post("/mfa/verify-setup")
def mfa_verify_setup(code: str = Body(..., embed=True), user = Depends(current_user), db: Session = Depends(get_db)):
    db_user = db.get(DimUser, user.id)
    if not db_user.mfa_secret:
        raise HTTPException(400, "MFA setup not initiated")
    totp = pyotp.totp.TOTP(db_user.mfa_secret)
    if not totp.verify(code):
        raise HTTPException(400, "Invalid MFA code")
    db_user.mfa_enabled = True
    db.commit()
    return {"status": "success"}

@router.post("/mfa/login")
def mfa_login(temp_token: str = Body(..., embed=True), code: str = Body(..., embed=True), db: Session = Depends(get_db)):
    from jose import JWTError
    try:
        payload = jwt.decode(temp_token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid or expired temporary token")
    
    db_user = db.get(DimUser, user_id)
    if not db_user or not db_user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled or user not found")
    
    totp = pyotp.totp.TOTP(db_user.mfa_secret)
    if not totp.verify(code):
        raise HTTPException(401, "Invalid MFA code")
        
    return {"access_token": create_access_token(db_user.id, db_user.role_name, db_user.organization_id), "token_type": "bearer"}

@router.get("/sso/login")
def sso_login():
    return RedirectResponse(url="/api/v1/auth/sso/callback?code=mock_enterprise_code_999")

@router.get("/sso/callback")
def sso_callback(code: str, db: Session = Depends(get_db)):
    if code != "mock_enterprise_code_999":
        raise HTTPException(400, "Invalid SSO code")
    
    sso_user_email = "enterprise.operator@vtab.local"
    sso_user_name = "Enterprise Operator"
    
    user = db.scalar(select(DimUser).where(DimUser.email == sso_user_email))
    if not user:
        user = DimUser(
            id=str(uuid.uuid4()),
            organization_id="00000000-0000-0000-0000-000000000001",
            email=sso_user_email,
            full_name=sso_user_name,
            password_hash=hash_password("auto-provisioned-sso"),
            role_name="engineer",
            is_active=True,
            is_verified=True,
            sso_provider="mock-idp",
            sso_id="uid-001"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_access_token(user.id, user.role_name, user.organization_id)
    return RedirectResponse(url=f"/?sso_token={token}")

@router.post("/register")
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("SELECT set_config('app.is_login', 'true', true)"))
    org_id = user_in.organization_id or "00000000-0000-0000-0000-000000000001"
    existing = db.scalar(select(DimUser).where(DimUser.email == user_in.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    verification_code = ''.join(random.choices(string.digits, k=6))
    
    PENDING_USERS[user_in.email] = {
        "organization_id": org_id,
        "email": user_in.email,
        "full_name": user_in.full_name,
        "password_hash": hash_password(user_in.password),
        "role_name": user_in.role_name or "viewer",
        "verification_code": verification_code,
        "expires_at": time.time() + 900  # 15 minutes expiration
    }
    
    # FOR DEVELOPMENT: Print the code to the terminal in case email goes to spam
    print(f"\n=======================================================")
    print(f"DEVELOPMENT MODE: Verification code for {user_in.email} is {verification_code}")
    print(f"=======================================================\n")
    
    # Send verification email asynchronously
    success = await send_verification_email(user_in.email, user_in.full_name, verification_code)
    
    if not success:
        if user_in.email in PENDING_USERS:
            del PENDING_USERS[user_in.email]
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please check the logs.")
        
    return {"email": user_in.email, "message": "Verification code sent to email"}

@router.post("/verify")
def verify(verify_in: UserVerify, db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("SELECT set_config('app.is_login', 'true', true)"))
    
    # Clean up expired pending users
    current_time = time.time()
    expired_emails = [e for e, d in PENDING_USERS.items() if d["expires_at"] < current_time]
    for e in expired_emails:
        del PENDING_USERS[e]
        
    pending_user = PENDING_USERS.get(verify_in.email)
    if not pending_user:
        raise HTTPException(status_code=404, detail="Registration session expired or not found")
        
    if pending_user["verification_code"] != verify_in.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Create the actual user now
    new_user = DimUser(
        id=str(uuid.uuid4()),
        organization_id=pending_user["organization_id"],
        email=pending_user["email"],
        full_name=pending_user["full_name"],
        password_hash=pending_user["password_hash"],
        role_name=pending_user["role_name"],
        is_active=True,
        is_verified=True,
        verification_code=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Remove from pending dictionary
    del PENDING_USERS[verify_in.email]
    
    # Return access token upon successful verification
    return {"access_token": create_access_token(new_user.id, new_user.role_name, new_user.organization_id), "token_type": "bearer"}

@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role_name, "organization_id": user.organization_id}

@router.get("/users")
def get_users(db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    users = db.scalars(select(DimUser)).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role_name, "is_active": u.is_active} for u in users]

@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, role_name: str = Body(..., embed=True), db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    user = db.get(DimUser, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.role_name = role_name
    db.commit()
    return {"status": "success"}

@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    user = db.get(DimUser, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"status": "success"}

class SupportQueryRequest(BaseModel):
    message: str
    attachment_name: str | None = None
    attachment_b64: str | None = None

@router.post("/support-query")
async def support_query(req: SupportQueryRequest):
    """Send a support query message to vitabsquare@gmail.com via Brevo."""
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    success = await send_query_email(req.message.strip(), req.attachment_name, req.attachment_b64)
    if not success:
        raise HTTPException(500, "Failed to send query. Please try again later.")
    return {"status": "sent"}
