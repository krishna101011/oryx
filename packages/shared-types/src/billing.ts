/**
 * Billing domain types — the first frontend-facing surface over the billing
 * foundation (PaymentProvider, plan_prices catalog, subscription state
 * machine). See apps/backend/src/oryx/services/billing/router.py.
 */
import type { WorkspacePlan } from './workspaces';

export type BillingCadence = 'monthly' | 'quarterly' | 'yearly';
export type BillingCurrency = 'USD' | 'INR';
export type PaymentProviderName = 'stripe' | 'razorpay';
/** Mirrors services/billing/state.py's SubscriptionStatus. */
export type SubscriptionStatus = 'pending' | 'active' | 'past_due' | 'canceled';

/** One real, decided price point from the plan_prices catalog. */
export interface PlanPrice {
  planId: string;
  tier: WorkspacePlan;
  cadence: BillingCadence;
  currency: BillingCurrency;
  amount: number;
}

export interface PlansResponse {
  plans: PlanPrice[];
}

/** The workspace's most recent subscription record. Vendor-specific ids are
 * intentionally not exposed here — the frontend only needs to know what's
 * happening, not the raw provider reference. `plan` is null for a PENDING
 * subscription whose tier hasn't been confirmed yet (the vendor hasn't
 * sent metadata identifying it) — never guessed. workspace_subscriptions
 * tracks tier, not cadence, so this is the tier alone, not a full plan_id. */
export interface ActiveSubscription {
  provider: PaymentProviderName;
  plan: WorkspacePlan | null;
  status: SubscriptionStatus;
  currency: BillingCurrency;
}

/** currentPlan is the REAL enforced tier (workspaces.plan) — the source of
 * truth for feature gating. subscription is null for a workspace that has
 * never subscribed (still on the free Glimpse default). */
export interface SubscriptionSummary {
  currentPlan: WorkspacePlan;
  subscription: ActiveSubscription | null;
}

/** currency is explicit, never inferred — it picks Stripe vs Razorpay and
 * must agree with planId's own currency (e.g. "focus_monthly_inr" requires
 * currency: "INR"). */
export interface SubscribeRequest {
  planId: string;
  currency: BillingCurrency;
}

export interface SubscribeResult {
  providerSubscriptionId: string;
  status: SubscriptionStatus;
}
