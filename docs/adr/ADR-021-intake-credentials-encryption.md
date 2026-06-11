# ADR-021 — Workspace-Scoped Envelope Encryption for Intake Credentials

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-022 (webhook signing), ADR-023 (no write-back)

---

## 1. Context

Phase 3 stores OAuth tokens (Gmail) and API credentials (api_pull). A
Gmail refresh token is the highest-impact secret in the system — it grants
standing read access to a user's inbox. The §17.1 risk matrix rates its
leak "catastrophic." DB-level encryption-at-rest belongs to the operator;
the application needs its own layer so a database dump alone is not a
credential dump.

## 2. Decision

`core/security/secrets.py` implements per-workspace envelope encryption:

- A master key (`INTAKE_KMS_KEY`, ≥32 bytes, environment-injected) never
  encrypts data directly. HKDF-SHA256 derives a per-workspace AES-256 key
  with info label `intake/v{version}/workspace/{workspace_id}`.
- AES-GCM is the AEAD primitive: tampering fails decryption loudly rather
  than yielding silently corrupt plaintext.
- The stored blob is `[version byte][12-byte nonce][ciphertext+tag]`. The
  leading version byte plus the `kms_key_version` column let the Appendix C
  rotation runbook re-encrypt in idempotent batches, skipping
  already-rotated rows.
- All credential I/O flows through `IntakeCredentialsRepository`
  (`store`/`load`/`delete`) — the only module that touches the
  `intake_credentials` table. Providers receive async token-provider
  callables and never see storage.

Why per-workspace derivation: a workspace export or hard-delete (CR-6)
can operate on one tenant's ciphertexts without touching others, and a
single leaked derived key exposes one workspace, not the fleet.

## 3. Consequences

### Positive
- DB dump alone is insufficient to recover tokens; tenant isolation holds
  at the crypto layer (tested: cross-workspace decryption fails).
- Key rotation is an online, idempotent, batched migration.

### Negative
- `INTAKE_KMS_KEY` becomes a single operational secret whose loss orphans
  every stored credential (mitigation: users reconnect; documented in the
  incident runbook).
- HKDF per call costs microseconds per credential access (negligible at
  intake's call rate).

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| One static AES key for all rows | No tenant isolation; rotation requires a full-table rewrite under lock |
| External KMS service (AWS KMS, Vault) | Phase 3 has no cloud-KMS dependency; the interface (version byte + repository seam) leaves the upgrade path open |
| Rely on disk/DB encryption only | Operator concern, not application defense; fails the "DB dump ≠ credential dump" bar |
