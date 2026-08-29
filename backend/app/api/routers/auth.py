from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


class LoginRequest(BaseModel):
    username: str
    password: str


# Baseline local supervisor credentials for offline development & initial deployment
DEMO_EXAMINERS = {
    "examiner@nciipc.gov.in": {
        "id": "usr-examiner-01",
        "password_hash": get_password_hash("SupervisorPass123!"),
        "role": "examiner"
    },
    "admin@nciipc.gov.in": {
        "id": "usr-admin-01",
        "password_hash": get_password_hash("AdminSupervisoryPass123!"),
        "role": "admin"
    }
}


@router.post("/login", response_model=TokenResponse, summary="Examiner Authentication")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username.strip().lower()
    user = DEMO_EXAMINERS.get(username)
    
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid examiner credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(subject=user["id"], role=user["role"])
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        user_id=user["id"]
    )
