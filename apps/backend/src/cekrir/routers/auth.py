import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from jwt import InvalidTokenError
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import User
from cekrir.db.repository import UserRepository
from cekrir.db.session import get_session
from cekrir.schemas import UserRead
from cekrir.services.auth import (
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)
from cekrir.services.email_verification import (
    EmailUnavailable,
    new_verification_token,
    prepare_verification,
    require_email_configuration,
    send_verification_email,
    verify_email,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class CredentialsInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
                raise ValueError("Enter a valid email address")
            return normalized
        return value


class RegisterInput(CredentialsInput):
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=72)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_is_at_most_72_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes")
        return value


class TokenRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserRead


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=1)


class VerificationInput(BaseModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class VerificationPending(BaseModel):
    detail: str = "Check your email for a verification link."


class RoleUpdate(BaseModel):
    role: Literal["admin", "member"]


def token_response(user: User, settings: Settings) -> TokenRead:
    return TokenRead(
        access_token=issue_token(user, settings, "access"),
        refresh_token=issue_token(user, settings, "refresh"),
        expires_in=int(ACCESS_TOKEN_LIFETIME.total_seconds()),
        refresh_expires_in=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=VerificationPending, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterInput,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        require_email_configuration(request.app.state.settings)
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    repository = UserRepository(session)
    if repository.by_email(payload.email):
        session.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    session.rollback()
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="member",
    )
    session.add(user)
    token = new_verification_token()
    try:
        session.flush()
        prepare_verification(session, user.id, token)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    try:
        send_verification_email(request.app.state.settings, user.email, token)
    except EmailUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="Account created; retry sending the verification email later"
        ) from exc
    return VerificationPending()


@router.post("/login", response_model=TokenRead)
def login(
    payload: CredentialsInput,
    request: Request,
    session: Session = Depends(get_session),
):
    user = UserRepository(session).by_email(payload.email)
    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
        or not verify_password(payload.password, user.password_hash)
    ):
        session.rollback()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return token_response(user, request.app.state.settings)


@router.post("/refresh", response_model=TokenRead)
def refresh(
    payload: RefreshInput,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        user_id = decode_token(payload.refresh_token, request.app.state.settings, "refresh")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc
    user = UserRepository(session).by_id(user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return token_response(user, request.app.state.settings)


@router.post("/verify-email")
def confirm_email(payload: VerificationInput, session: Session = Depends(get_session)):
    if not verify_email(session, payload.token):
        session.rollback()
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    session.commit()
    return {"detail": "Email verified. You can now sign in."}


@router.post("/resend-verification", response_model=VerificationPending)
def resend_verification(
    payload: CredentialsInput,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        require_email_configuration(request.app.state.settings)
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    user = UserRepository(session).by_email(payload.email)
    if (
        user is None
        or user.email_verified_at is not None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        session.rollback()
        return VerificationPending()
    user_id, email = user.id, user.email
    token = new_verification_token()
    prepared = prepare_verification(session, user_id, token)
    session.commit()
    if prepared:
        try:
            send_verification_email(request.app.state.settings, email, token)
        except EmailUnavailable as exc:
            raise HTTPException(
                status_code=503, detail="Verification email could not be sent"
            ) from exc
    return VerificationPending()


@router.get("/verify-email", response_class=HTMLResponse, include_in_schema=False)
def verification_page():
    return HTMLResponse(
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Verify email</title></head><body><main><h1>Verify your email</h1>
        <p id="message">Confirm your email address to finish registration.</p>
        <button id="verify" type="button">Verify email</button></main><script>
        const token = new URLSearchParams(location.search).get('token');
        history.replaceState(null, '', location.pathname);
        document.getElementById('verify').onclick = async () => {
          const button = document.getElementById('verify');
          button.disabled = true;
          try {
            const response = await fetch(location.pathname, {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({token})
            });
            document.getElementById('message').textContent = response.ok
              ? 'Email verified. You can now sign in.'
              : 'The link is invalid or expired. Request another verification email.';
          } catch {
            document.getElementById('message').textContent = 'Could not verify. Please try again.';
            button.disabled = false;
          }
        };
        </script></body></html>""",
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


@router.get("/users", response_model=list[UserRead])
def list_users(session: Session = Depends(get_session)):
    return UserRepository(session).list_users()


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_role(
    user_id: UUID,
    payload: RoleUpdate,
    session: Session = Depends(get_session),
):
    user = UserRepository(session).by_id(user_id)
    if user is None:
        session.rollback()
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Reassign the user's locations before changing their role"
        ) from exc
    return UserRead.model_validate(user)
