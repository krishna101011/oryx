/**
 * Phase 3 — inbound webhook envelope.
 * Used as documentation of the wire shape; not consumed by mobile in Batch 1.
 */
export interface WebhookEnvelope {
  workspaceId: string;
  intakeSourceId: string;
  signature: string;        // hmac-sha256=<hex>
  timestamp: number;        // unix seconds
  idempotencyKey: string;
  body: unknown;
}
