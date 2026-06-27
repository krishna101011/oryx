# ADR-041 — Publish-Target Credential Encryption Strategy

**Status:** Accepted — implemented in Phase 5 Wave D
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-021 (intake credentials envelope encryption), ADR-040 (channel adapter protocol), ADR-046 (Phase 5→6 boundary)

---

## 1. Context

Publish targets hold live secrets: OAuth access tokens, SendGrid API keys, SMTP
passwords, Notion integration tokens, webhook signing secrets. These are written
once when a target is configured and read only at delivery time, inside the
engine, just before the adapter call. They must survive at rest encrypted and
must never leak through any read path.

Phase 3 already does workspace-derived envelope encryption (HKDF per workspace)
for intake tokens (ADR-021). The Phase 5 architecture, however, froze a different,
simpler contract for publish credentials: `encrypt_credentials(dict) ->
(ciphertext, iv)` with a single global key. Reusing the workspace-envelope shape
would mean changing that frozen contract.

## 2. Decision

**AES-256-GCM with a single global publish key, in a dedicated module
(`core/credential_crypto.py`), separate from Phase 3's `secrets.py`.**

- **Algorithm:** AES-256-GCM via the `cryptography` library's `AESGCM` — the same
  AEAD primitive Phase 3 uses, so there is one AEAD choice across the codebase.
- **IV:** a fresh random **12-byte** nonce per call (`os.urandom(12)`); GCM is
  catastrophically unsafe under nonce reuse, so this is per-record, never derived
  or reused. The GCM auth tag is appended to the ciphertext by `AESGCM` and
  verified on decrypt (tamper → raises).
- **Storage:** `(ciphertext, iv)` go into `publish_targets.credentials` /
  `credentials_iv` (BYTEA). The plaintext is a JSON-serialisable dict of channel
  credential fields.
- **Key:** `ORYX_PUBLISH_KEY` — a base64-encoded 32-byte secret (base64 so a raw
  binary key survives `.env` transport, matching how a real secrets manager would
  hand it over). A configured value that does not decode to exactly 32 bytes is a
  **hard error** — the module never silently pads or truncates a key.

**Placeholder-vs-real status (verified, current).** `config.Settings.oryx_publish_key`
defaults to `None`. When unset, `_load_key()` falls back to an obvious,
clearly-labelled 32-byte dev placeholder (`DEV-ONLY-PLACEHOLDER-PUBLISH-KEY`) so
the unit suite and local dev run without a configured secret. The 2026-06-26
env-var audit confirmed `ORYX_PUBLISH_KEY` is present and correctly named in the
real local `.env`; it **must** be a securely-generated 32-byte secret before
staging/prod — the placeholder never ships.

**The plaintext is write-only.** Credentials are decrypted exactly once, inside
`PublishingEngine._publish_one`, immediately before the adapter call. They are
**never** logged (confirmed by the Wave F security scan — `credential_crypto.py`
emits no log lines at all), never returned in any API response, and never placed
in an event payload (ADR-046's boundary event carries ids and the channel name
only).

## 3. Consequences

### Positive
- Honours the frozen `encrypt_credentials(dict) -> (ciphertext, iv)` contract
  without disturbing Phase 3's workspace-envelope scheme.
- One AEAD primitive across the codebase; per-record random IV closes the GCM
  nonce-reuse footgun; tamper is detected, not silently accepted.
- Hard-fail on a wrong-length key turns a silent crypto weakness into a loud
  startup/usage error.

### Negative
- A single global key is a coarser blast radius than Phase 3's per-workspace
  envelope: one key compromise exposes all publish credentials. Accepted for this
  phase as the frozen contract; the module boundary makes a later move to envelope
  encryption a contained change.
- A dev placeholder that "just works" risks a careless prod deploy with no real
  key. Mitigated by the loud `WARNING` in config, the obvious placeholder string,
  and the env-var audit discipline (see the skill's Operational Reality log).

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Reuse Phase 3 workspace-envelope encryption | Changes the frozen `encrypt_credentials(dict)->(ct,iv)` contract; over-engineered for write-once/read-at-delivery secrets. |
| AES-CBC + separate HMAC | Two primitives to get right vs one AEAD; GCM gives confidentiality + integrity in one verified construction. |
| Reuse a single IV / derive IV from data | GCM nonce reuse is catastrophic — a fixed or derived IV defeats the cipher. Random per-record is mandatory. |
| Store credentials in plaintext, rely on DB-at-rest encryption | Any read path (a stray log, an over-broad API serializer) leaks them; application-level encryption keeps the plaintext write-only. |
| Pad/truncate a wrong-length key to fit | Silently weakens the key; a hard error is the only safe response. |
