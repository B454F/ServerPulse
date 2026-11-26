
import os
import time
import uuid
import sqlite3

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    Depends
)

from pydantic import BaseModel, EmailStr, Field

from database_v2 import get_db

from security import (
    hash_password,
    verify_password,
    generate_token,
    hash_token,
    SESSION_DURATION
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

COOKIE_NAME = "serverpulse_session"

SECURE_COOKIE = (
    os.getenv("SECURE_COOKIE", "true").lower() == "true"
)

DUMMY_HASH = hash_password(generate_token())


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    with get_db() as conn:
        user = conn.execute("""
            SELECT
                users.id,
                users.email,
                users.display_name,
                users.created_at

            FROM sessions

            JOIN users
                ON sessions.user_id = users.id

            WHERE sessions.token_hash = ?
            AND sessions.expires_at > ?
            AND users.is_active = 1
        """, (
            hash_token(token),
            int(time.time())
        )).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session"
        )

    return dict(user)


@router.post("/register", status_code=201)
def register(data: RegisterRequest):

    email = str(data.email).strip().lower()
    display_name = data.display_name.strip()

    if len(display_name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Invalid display name"
        )

    user_id = str(uuid.uuid4())
    created_at = int(time.time())
    password_hash = hash_password(data.password)

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users (
                    id,
                    email,
                    display_name,
                    password_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                email,
                display_name,
                password_hash,
                created_at
            ))

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Account already exists"
        )

    return {
        "message": "Account created successfully",
        "user_id": user_id
    }


@router.post("/login")
def login(data: LoginRequest, response: Response):

    email = str(data.email).strip().lower()

    with get_db() as conn:
        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
            AND is_active = 1
        """, (email,)).fetchone()

    hashed = user["password_hash"] if user else DUMMY_HASH

    valid = verify_password(data.password, hashed)

    if not user or not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = generate_token()
    now = int(time.time())

    with get_db() as conn:
        conn.execute("""
            DELETE FROM sessions
            WHERE expires_at <= ?
        """, (now,))

        conn.execute("""
            INSERT INTO sessions (
                token_hash,
                user_id,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            hash_token(token),
            user["id"],
            now,
            now + SESSION_DURATION
        ))

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SECURE_COOKIE,
        samesite="strict",
        max_age=SESSION_DURATION,
        path="/"
    )

    return {
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"]
        }
    }


@router.post("/logout")
def logout(request: Request, response: Response):

    token = request.cookies.get(COOKIE_NAME)

    if token:
        with get_db() as conn:
            conn.execute("""
                DELETE FROM sessions
                WHERE token_hash = ?
            """, (hash_token(token),))

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=SECURE_COOKIE,
        httponly=True,
        samesite="strict"
    )

    return {
        "message": "Logout successful"
    }


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
