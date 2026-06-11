# ADR-023 — No Write-Back Policy

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-021 (credentials), ADR-015 (provider layer)

---

## 1. Context

Intake reads a user's most sensitive curated space — their inbox. The
product promise (§4.9) is that connecting a source can never change it:
no sends, no replies, no label changes, no deletions, on any vendor.
A policy that lives only in documentation erodes one convenient helper
function at a time; this one is enforced structurally.

## 2. Decision

The policy is enforced at four independent layers:

1. **OAuth scope.** `REQUESTED_SCOPES` is exactly
   `("https://www.googleapis.com/auth/gmail.readonly",)`. Google itself
   rejects write calls made with this token.
2. **Grant verification.** The token exchange refuses a response whose
   granted scope set is not a superset match of the requested read-only
   scope — and `build_auth_url` raises at call time if the constant has
   been tampered with.
3. **Client surface.** `providers/gmail/client.py` defines list/get
   operations only and asserts no write-shaped functions are defined.
   RSS is GET-only by nature; webhooks are inbound-only; api_pull builds
   only GET requests.
4. **Tests.** `test_security_invariants.py` fails the build if the client
   surface grows a write-shaped name, if the scope constant changes, or
   if the tamper assertion is removed.

The single deliberate exception: best-effort **revoke** of our own grant
(disconnect, CR-6 cascade). Revoking our own access is the opposite of
mutating user data.

## 3. Consequences

### Positive
- A future "mark processed items read" feature request requires an
  explicit supersession of this ADR — a conversation, not a drive-by PR.
- The guarantee is testable and survives refactors.

### Negative
- Genuinely useful write features (drafting replies in Phase 5+) must go
  through a separate, explicitly-consented surface — never piggyback on
  the intake grant.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Policy by code review only | Erodes silently; the readonly scope is the only enforcement a vendor honors |
| Broader scope now "for later flexibility" | Catastrophic blast radius on credential leak; violates the §17.1 risk posture |
