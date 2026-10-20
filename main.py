"""JWT registration/login demo for hands-on FastAPI practice (Python 3.10+)."""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from database import create_user, get_user, init_db

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError("Set JWT_SECRET to a strong, random 32+ character value in .env")

JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 30
hasher = PasswordHasher()  # Argon2id by default
DUMMY_HASH = hasher.hash("not-an-actual-account-password")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class UserPublic(BaseModel):
    username: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def hash_password(plain_password: str) -> str:
    return hasher.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return hasher.verify(stored_hash, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    payload = {"sub": username, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise unauthorized
    except jwt.InvalidTokenError:
        raise unauthorized from None

    user = get_user(username)
    if user is None:
        raise unauthorized
    return UserPublic(username=user["username"], full_name=user["full_name"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="JWT Authentication Practice", lifespan=lifespan)


@app.post("/register", status_code=201, response_model=UserPublic)
def register(body: RegisterRequest):
    password_hash = hash_password(body.password)
    created = create_user(body.username, password_hash, body.full_name)
    if not created:
        raise HTTPException(status_code=409, detail="Username already taken")
    return UserPublic(username=body.username, full_name=body.full_name)


@app.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form.username)
    # Check a dummy hash even if user does not exist to reduce timing differences.
    stored_hash = user["password_hash"] if user else DUMMY_HASH
    valid_password = verify_password(form.password, stored_hash)
    if user is None or not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user["username"])
    return TokenResponse(access_token=token)


@app.get("/me", response_model=UserPublic)
def read_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user
