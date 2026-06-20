# ORYX — Security Notes (Phase 2)

This document captures Phase 2's security posture: what the code guarantees, what the tests verify, and what is explicitly the operator's responsibility.

---

## 1. Credentials at rest

**Passwords** — Argon2id (OWASP-recommended parameters: `time_cost=3`, `memory_cost=64 MiB`, `parallelism=2`, `hash_len=32`). Hashes are self-describing; parameter changes do not require re-hashing existing passwords. Phase 2 ships a 10-char minimum + letter + digit policy (server-side authoritative); the client validates only as a UX nicety.

**Refresh tokens** — High-entropy opaque strings (`secrets.token_urlsafe(48)`). The DB stores only the **SHA-256 hash** in `sessions.refresh_token_hash` so a database leak does not leak any usable credentials.

**Access tokens (JWT)** — HS256 signed with `JWT_SECRET`. Claims are intentionally minimal — `{sub, wsp, sid, iat, exp, jti}` — no email, no profile data, no PII. 15-minute TTL. 30s clock-skew tolerance.

**MFA secrets** — column reserved (`accounts.mfa_secret`). Phase 2 ships interface only; encryption-at-rest for the secret happens when MFA is implemented (Phase 2.x patch).

**Tests covering this layer:** `tests/unit/test_passwords.py`, `tests/unit/test_jwt.py`.

---

## 2. Session lifecycle

**Rotation.** Every successful refresh issues a new refresh token, marks the old one revoked with `revoked_reason='rotation'`, and links the new session via `parent_session_id`. Mobile SecureStore is updated atomically.

**Reuse detection.** Presenting a revoked refresh token triggers `revoke_chain()` — every descendant of the compromised root session is revoked with `revoked_reason='reuse_detected'`. The endpoint returns `AUTH_REFRESH_REUSE_DETECTED`; the mobile client treats it as terminal and signs out.

**Sign-out everywhere.** `POST /v1/auth/signout-all` revokes every active session for the account.

**Cleanup.** Sessions with `expires_at < now() - 30 days` should be hard-deleted by a periodic job (operator concern; not Phase 2 scope).

**Tests covering this layer:** `tests/integration/test_auth_flow.py::test_refresh_rotates_and_old_token_is_invalid`.

---

## 3. Account-level abuse controls

| Control | Trigger | Mechanism |
|---|---|---|
| **Signin rate limit** | 5 attempts / 10 min per IP (sliding window) | `RateLimitMiddleware`. In-memory per-process — replace with Redis before horizontal scaling. |
| **Signup rate limit** | 5 attempts / 10 min per IP | Same |
| **Account lockout** | 10 consecutive failed signins on one account | `accounts.locked_until` set 15 min ahead; the correct password is also rejected during the lockout window |
| **Email enumeration resistance** | Bogus email + any password | Performs a dummy Argon2 verify before returning `AUTH_INVALID_CREDENTIALS` so the response timing matches the real-account path |

**Tests covering this layer:** `tests/integration/test_security.py`.

---

## 4. Authorization

**Identity model.** Every request resolves a `CurrentPrincipal` (account_id, workspace_id, session_id) from the bearer token. Requests without a valid bearer get `AUTH_REQUIRED`.

**Workspace isolation.** Every domain query joins on `workspace_id = active_workspace_id`. Active workspace is resolved via `WorkspaceMember`; if the principal's claimed workspace has no membership row, `WORKSPACE_NOT_FOUND`.

**Account isolation.** `GET /v1/users/{id}` requires `id == current_account.id`; otherwise `PERMISSION_DENIED`.

**Capability checks.** `require_capability(c)` runs on every protected route. Phase 2's role catalog:

- `owner` — `*` (all)
- `admin` — `research.*`, `settings.*`, `integrations.*`, `content.*`, `activity.*`
- `editor` — `research.write`, `research.read`, `content.*`, `activity.read`
- `reader` — `research.read`, `content.read`, `activity.read`

Phase 2 ships single-user mode (every user is owner of their own workspace), so the check never denies in practice. The dependency runs in every request path so Phase 4's first real check ships exercised, not freshly broken.

**Platform admin.** `accounts.is_platform_admin = true` is the only path to override flags via `POST /v1/admin/feature-flags/overrides`. Never exposed in any product API.

**Tests covering this layer:** `tests/unit/test_capabilities.py`, `tests/integration/test_security.py::test_account_isolation_blocks_other_users`.

---

## 5. Observability and PII

**Structured JSON logs** — one event per line. Every record carries `request_id`, `service`, `event`, `level`.

**Redaction.** `RedactingFormatter` strips known PII fields (`email`, `password`, `password_hash`, `token`, `access_token`, `refresh_token`, `phone`, `name`, `address`, `ip_address`) at the formatter level. Any code path that puts such a value in `extra={}` will see `[redacted]` in the sink. This makes accidental PII logging a structural impossibility for the listed keys.

**Auth audit log** — `auth_audit_log` table receives an immutable row for every auth-relevant event: `signup`, `signin_success`, `signin_failure`, `signout`, `signout_all`, `refresh`, `refresh_reuse_detected`, `lockout`, `password_change`. Includes `account_id`, `ip_address`, `user_agent`, and event-specific `data` jsonb.

**Stack traces.** Unhandled exceptions return a generic `INTERNAL_ERROR` envelope; the full traceback hits logs only, never the wire.

**Tests covering this layer:** `tests/unit/test_logging_redaction.py`.

---

## 6. Transport

**CORS** — `Settings.cors_origins` is an explicit allowlist. Default covers Expo dev (`:8081`, `:19006`); production deploys must override.

**HTTPS** — terminated at the operator's load balancer / ingress. The app does not handle TLS itself.

**Headers exposed** — only `X-Request-Id` and `X-Response-Time` (for correlation and debugging).

---

## 7. Operator responsibilities (deferred from Phase 2)

These are real security concerns whose ownership is operations, not application code. Phase 2 surfaces the surface; the rollout playbook covers these.

1. **`JWT_SECRET` rotation.** The dev default is a placeholder. Production must set a high-entropy value. A rotation drill (zero-downtime, dual-key window) is documented separately.
2. **Database encryption at rest.** Phase 2 stores Argon2 hashes and SHA-256 refresh hashes, not plaintext credentials, but operators should enable at-rest encryption regardless.
3. **TLS termination** as above.
4. **Backup retention and access control** on the Postgres instance.
5. **Log retention.** `auth_audit_log` is append-only application-side; operators decide ship-to-SIEM cadence and retention windows.
6. **`pg_hba.conf` / network ACLs** on the database tier.
7. **Dependency vulnerability scanning** — Dependabot (planned in repo settings) + periodic `pip-audit` / `npm audit`.

---

## 8. Phase 2 exit checklist (security only)

- [x] Argon2id with OWASP parameters
- [x] Refresh tokens hashed at rest, opaque on the wire
- [x] JWT signed; minimal claims; clock skew tolerance
- [x] Rotation with reuse detection → chain revocation
- [x] Rate limit on `/auth/signin` and `/auth/signup`
- [x] Account lockout after threshold
- [x] Account isolation enforced
- [x] Workspace isolation enforced
- [x] Capability checks running on every protected route
- [x] PII redaction in logs
- [x] Auth audit log for every auth event
- [x] MFA stubs return 501 cleanly (no information leak)
- [x] Unit + integration tests covering all of the above

---

## Running the security test pass

Unit tests run anywhere:

```bash
cd apps/backend
uv run pytest tests/unit -q
```

Integration tests require a reachable Postgres with the Phase 2 migration applied:

```bash
# 1. bring up a disposable test DB (docker-compose example)
docker run -d --rm --name oryx-test-pg \
  -e POSTGRES_USER=anant -e POSTGRES_PASSWORD=anant -e POSTGRES_DB=anant \
  -p 55432:5432 postgres:16
export ORYX_TEST_DB=postgresql+asyncpg://anant:anant@localhost:55432/anant
export DATABASE_URL="$ORYX_TEST_DB"
uv run alembic upgrade head

# 2. run the full suite
uv run pytest -q

# 3. just the security pass
uv run pytest -m security -q

# 4. tear down
docker stop oryx-test-pg
```

CI runs the unit suite always and the integration suite when the test DB service is available.
