/**
 * 4-step onboarding state machine.
 * Each step is durable: a POST commits the step's choices, server returns next step.
 */
export type OnboardingStep =
  | 'welcome'
  | 'focus_sources'
  | 'notifications_permissions'
  | 'style_strictness';

export type OnboardingState = 'incomplete' | 'complete';

import type { Focus, ContentStyle, VerificationStrictness, NotificationFrequency } from './preferences';

/** Per-step body. Server validates and ignores fields not relevant to the step. */
export interface OnboardingStepRequest {
  step: OnboardingStep;
  // Step 2 — focus + sources
  focus?: Focus;
  customTopics?: string[];
  enabledSourceKeys?: string[];
  // Step 3 — notifications + permissions
  notificationFrequency?: NotificationFrequency;
  pushPermissionGranted?: boolean;
  // Step 4 — style + strictness
  contentStyle?: ContentStyle;
  verificationStrictness?: VerificationStrictness;
}

export interface OnboardingStepResponse {
  state: OnboardingState;
  nextStep: OnboardingStep | null;
}
