"""Canonical error envelope and exception types.

Every exception crossing an HTTP boundary maps to the same wire shape:
    { "error": { "code": "...", "message": "...", "details": {...}, "requestId": "..." } }
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from oryx.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base for all application errors. Subclass for domain-specific errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "Internal server error"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}


# --- generic ---
class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404
    message = "Resource not found"


class ValidationError(AppError):
    code = "VALIDATION_FAILED"
    http_status = 422
    message = "Request validation failed"


class BadRequestError(AppError):
    """Service-layer 400. Used where the spec mandates HTTP 400 (e.g. an
    analyst note that is present in the body but empty) — distinct from the
    422 schema-validation path so the check is enforced in the service."""

    code = "VALIDATION_FAILED"
    http_status = 400
    message = "Bad request"


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    http_status = 429
    message = "Too many requests"


class PreconditionFailedError(AppError):
    """Service-layer 409 — a request was rejected by a gate, not by schema.
    Used for the research-packet readiness gate; blockers ride in `details`."""

    code = "VALIDATION_FAILED"
    http_status = 409
    message = "Precondition not met"


class NotImplementedFeatureError(AppError):
    code = "NOT_IMPLEMENTED"
    http_status = 501
    message = "Not implemented"


class ProviderHttpError(AppError):
    code = "PROVIDER_ERROR"
    http_status = 502
    message = "Upstream provider failure"


# --- auth ---
class AuthRequiredError(AppError):
    code = "AUTH_REQUIRED"
    http_status = 401
    message = "Authentication required"


class AuthInvalidCredentialsError(AppError):
    code = "AUTH_INVALID_CREDENTIALS"
    http_status = 401
    message = "Incorrect email or password"


class AuthTokenExpiredError(AppError):
    code = "AUTH_TOKEN_EXPIRED"
    http_status = 401
    message = "Access token expired"


class AuthRefreshInvalidError(AppError):
    code = "AUTH_REFRESH_INVALID"
    http_status = 401
    message = "Refresh token revoked or expired"


class AuthRefreshReuseDetectedError(AppError):
    code = "AUTH_REFRESH_REUSE_DETECTED"
    http_status = 401
    message = "Session chain compromised"


class AuthEmailTakenError(AppError):
    code = "AUTH_EMAIL_TAKEN"
    http_status = 409
    message = "Email already registered"


class AuthPasswordWeakError(AppError):
    code = "AUTH_PASSWORD_WEAK"
    http_status = 422
    message = "Password does not meet policy"


class AuthRateLimitedError(AppError):
    code = "AUTH_RATE_LIMITED"
    http_status = 429
    message = "Too many authentication attempts"


class AuthAccountLockedError(AppError):
    code = "AUTH_ACCOUNT_LOCKED"
    http_status = 423
    message = "Account temporarily locked"


class AuthMfaRequiredError(AppError):
    code = "AUTH_MFA_REQUIRED"
    http_status = 401
    message = "MFA challenge required"


class AuthMfaInvalidError(AppError):
    code = "AUTH_MFA_INVALID"
    http_status = 401
    message = "MFA code invalid"


# --- permissions / workspace ---
class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    http_status = 403
    message = "Permission denied"


class FeatureDisabledError(AppError):
    code = "FEATURE_DISABLED"
    http_status = 403
    message = "Feature not enabled"


class WorkspaceNotFoundError(AppError):
    code = "WORKSPACE_NOT_FOUND"
    http_status = 404
    message = "Workspace not found or not accessible"


class OnboardingRequiredError(AppError):
    code = "ONBOARDING_REQUIRED"
    http_status = 409
    message = "Onboarding not complete"


# --- billing ---
class PaymentProviderUnavailableError(AppError):
    """The real, honest response for PaymentProviderError today: no live
    Stripe/Razorpay credentials or vendor Price/Plan object is configured
    yet. 503 (not 500) — this is a known, expected state, not a crash."""

    code = "PAYMENT_PROVIDER_UNAVAILABLE"
    http_status = 503


# --- training/academy (Phase 8 Wave A) ---
class VideoProviderUnavailableError(AppError):
    """The real, honest response for VideoProviderError today: no live
    Cloudflare Stream credentials are configured yet. 503 (not 500) — this
    is a known, expected state, not a crash. Mirrors
    PaymentProviderUnavailableError's shape exactly."""

    code = "VIDEO_PROVIDER_UNAVAILABLE"
    http_status = 503


# --- team/workspace (Rev 2) ---
class InviteNotFoundError(AppError):
    code = "INVITE_NOT_FOUND"
    http_status = 404
    message = "Invite not found"


class InviteInvalidError(AppError):
    """Covers every "not currently acceptable" state in one bucket: expired,
    revoked, or already accepted (the losing side of a real accept-invite
    race lands here too — a clean, honest response, not a 500)."""

    code = "INVITE_INVALID"
    http_status = 410
    message = "Invite is no longer valid"


class InviteEmailMismatchError(AppError):
    code = "INVITE_EMAIL_MISMATCH"
    http_status = 403
    message = "This invite was sent to a different email address"
    message = "Payments aren't configured yet"


# --- envelope helpers ---
def _envelope(
    code: str, message: str, request_id: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {"code": code, "message": message, "requestId": request_id}
    }
    if details:
        body["error"]["details"] = details
    return body


def _get_request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else "unknown"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = _get_request_id(request)
    logger.warning(
        "app_error",
        extra={"code": exc.code, "request_id": request_id, "details": exc.details},
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_envelope(exc.code, exc.message, request_id, exc.details),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = _get_request_id(request)
    code = "NOT_FOUND" if exc.status_code == 404 else "INTERNAL_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(code, str(exc.detail), request_id),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=422,
        content=_envelope(
            "VALIDATION_FAILED",
            "Request validation failed",
            request_id,
            {"errors": exc.errors()},
        ),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    request_id = _get_request_id(request)
    logger.exception(
        "unhandled_exception",
        extra={"request_id": request_id, "type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=500,
        content=_envelope("INTERNAL_ERROR", "Internal server error", request_id),
    )
