from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.schemas import TokenRead, UserRead, VerificationPending
from cekrir.services import accounts
from cekrir.services.email_verification import EmailUnavailable
from cekrir.validation.auth import (
    CredentialsInput,
    RefreshInput,
    RegisterInput,
    RoleUpdate,
    VerificationInput,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=VerificationPending, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInput, request: Request, session: Session = Depends(get_session)):
    try:
        accounts.register_account(session, request.app.state.settings, payload)
    except accounts.AccountConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return VerificationPending()


@router.post("/login", response_model=TokenRead)
def login(payload: CredentialsInput, request: Request, session: Session = Depends(get_session)):
    try:
        return accounts.login_account(session, request.app.state.settings, payload)
    except accounts.InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenRead)
def refresh(payload: RefreshInput, request: Request, session: Session = Depends(get_session)):
    try:
        return accounts.refresh_account(session, request.app.state.settings, payload.refresh_token)
    except accounts.InvalidRefreshToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/verify-email")
def confirm_email(payload: VerificationInput, session: Session = Depends(get_session)):
    try:
        accounts.confirm_account_email(session, payload.token)
    except accounts.InvalidVerificationToken as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"detail": "Email verified. You can now sign in."}


@router.post("/resend-verification", response_model=VerificationPending)
def resend_verification(
    payload: CredentialsInput, request: Request, session: Session = Depends(get_session)
):
    try:
        accounts.resend_account_verification(session, request.app.state.settings, payload)
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
    return accounts.list_accounts(session)


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_role(user_id: UUID, payload: RoleUpdate, session: Session = Depends(get_session)):
    try:
        return accounts.change_role(session, user_id, payload.role)
    except accounts.UserNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except accounts.RoleChangeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
