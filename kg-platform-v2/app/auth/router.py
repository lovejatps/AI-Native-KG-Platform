"""Auth router exposing ``/auth/register`` and ``/auth/login`` endpoints.

The endpoints return a JWT token that must be provided in the ``Authorization``
header (``Bearer <token>``) for any protected route.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .schemas import UserCreate, UserLogin, TokenResponse
from .models import create_user, authenticate_user
from .utils import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

# FastAPI security scheme – used by protected endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(user: UserCreate):
    if not create_user(user.email, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )
    access_token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin):
    if not authenticate_user(user.email, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=access_token)


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]
