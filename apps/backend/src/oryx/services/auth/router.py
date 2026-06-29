"""Auth router — /v1/auth/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.dependencies import (
    CurrentPrincipal,
    db_session,
    envelope,
    get_current_account,
    get_principal,
    get_request_id,
)
from oryx.core.errors import NotImplementedFeatureError
from oryx.core.models import Account
from oryx.core.security.cookies import clear_session_cookie, set_session_cookie
from oryx.services.auth.providers.email.base import EmailMessage
from oryx.services.auth.providers.email.log_only import LogOnlyEmailProvider
from oryx.services.auth.service import AuthService, IssuedTokens
from oryx.shared.types import (
    Account as AccountSchema,
)
from oryx.shared.types import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MfaVerifyRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SigninRequest,
    SigninResponse,
    SignupRequest,
    SignupResponse,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_email_provider = LogOnlyEmailProvider()


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _tokens_to_pair(tokens: IssuedTokens) -> TokenPair:
    return TokenPair(
        accessToken=tokens.access_token,
        refreshToken=tokens.refresh_token,
        accessTokenExpiresAt=tokens.access_token_expires_at,
        refreshTokenExpiresAt=tokens.refresh_token_expires_at,
        sessionId=str(tokens.session_id),
        accountId=str(tokens.account_id),
    )


def _account_to_schema(account: Account) -> AccountSchema:
    return AccountSchema(
        id=str(account.id),
        email=account.email,
        status=account.status,
        emailVerified=account.email_verified_at is not None,
        createdAt=account.created_at,
    )


@router.post("/signup")
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = AuthService(db)
    tokens = await svc.signup(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        device_id=body.device_id,
        device_label=body.device_label,
        device_platform=body.device_platform,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    account = await svc.repo.get_account_by_id(tokens.account_id)
    assert account is not None
    # Additive: native reads tokens from the body; web persists via this cookie.
    set_session_cookie(response, tokens.access_token, get_settings())
    payload = SignupResponse(
        tokens=_tokens_to_pair(tokens), account=_account_to_schema(account)
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post("/signin")
async def signin(
    body: SigninRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = AuthService(db)
    tokens = await svc.signin(
        email=body.email,
        password=body.password,
        device_id=body.device_id,
        device_label=body.device_label,
        device_platform=body.device_platform,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    account = await svc.repo.get_account_by_id(tokens.account_id)
    assert account is not None
    # Additive: native reads tokens from the body; web persists via this cookie.
    set_session_cookie(response, tokens.access_token, get_settings())
    payload = SigninResponse(
        tokens=_tokens_to_pair(tokens), account=_account_to_schema(account)
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post("/refresh")
async def refresh(
    body: RefreshRequest, request: Request, db: AsyncSession = Depends(db_session)
) -> dict:
    svc = AuthService(db)
    tokens = await svc.refresh(
        refresh_token=body.refresh_token,
        device_id=body.device_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return envelope(
        _tokens_to_pair(tokens).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.post("/signout")
async def signout(
    request: Request,
    response: Response,
    principal: CurrentPrincipal = Depends(get_principal),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = AuthService(db)
    await svc.signout(session_id=principal.session_id, account_id=principal.account_id)
    # Native already discards its stored tokens; clear the web session cookie too.
    clear_session_cookie(response, get_settings())
    return envelope({"ok": True}, request_id=get_request_id(request))


@router.post("/signout-all")
async def signout_all(
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = AuthService(db)
    await svc.signout_all(account_id=principal.account_id)
    return envelope({"ok": True}, request_id=get_request_id(request))


# ---------------- password ----------------

@router.post("/password/change")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = AuthService(db)
    await svc.change_password(
        account_id=account.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return envelope({"ok": True}, request_id=get_request_id(request))


@router.post("/password/forgot")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Privacy: same response regardless of whether the email exists.
    svc = AuthService(db)
    account = await svc.repo.get_account_by_email(body.email)
    if account is not None:
        # Phase 2: log-only provider. Phase 6 sends a real email with a signed token.
        await _email_provider.send(
            EmailMessage(
                to=body.email,
                template="password_reset",
                variables={"account_id": str(account.id)},
            )
        )
    return envelope({"ok": True}, request_id=get_request_id(request))


@router.post("/password/reset")
async def reset_password(
    body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(db_session)
) -> dict:
    # Token-based reset is Phase 6 (requires email delivery). Phase 2 stubs 501.
    raise NotImplementedFeatureError("Password reset requires email delivery (Phase 6)")


# ---------------- MFA stubs (Phase 2: interface only) ----------------

@router.post("/mfa/setup")
async def mfa_setup(_account: Account = Depends(get_current_account)) -> dict:
    raise NotImplementedFeatureError("MFA setup not implemented")


@router.post("/mfa/verify")
async def mfa_verify(
    _body: MfaVerifyRequest, _account: Account = Depends(get_current_account)
) -> dict:
    raise NotImplementedFeatureError("MFA verify not implemented")


@router.post("/mfa/disable")
async def mfa_disable(_account: Account = Depends(get_current_account)) -> dict:
    raise NotImplementedFeatureError("MFA disable not implemented")
