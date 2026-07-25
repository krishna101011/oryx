import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type {
  BillingCadence,
  BillingCurrency,
  PlanPrice,
  SubscriptionStatus,
  WorkspacePlan,
} from '@oryx/shared-types';
import { isApiError } from '../../../lib/errors';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { usePlans, useSubscribe, useSubscriptionSummary } from '../hooks/useBilling';

const TIER_LABEL: Record<WorkspacePlan, string> = {
  glimpse: 'Glimpse',
  focus: 'Focus',
  clarity: 'Clarity',
  vision: 'Vision',
};

const CADENCE_LABEL: Record<BillingCadence, string> = {
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
};

const STATUS_COPY: Record<SubscriptionStatus, string> = {
  pending: 'Pending confirmation',
  active: 'Active',
  past_due: 'Payment past due',
  canceled: 'Canceled',
};

const CURRENCIES: BillingCurrency[] = ['USD', 'INR'];
const PAID_TIERS: WorkspacePlan[] = ['focus', 'clarity', 'vision'];
const CADENCES: BillingCadence[] = ['monthly', 'quarterly', 'yearly'];

const CURRENCY_SYMBOL: Record<BillingCurrency, string> = { USD: '$', INR: '₹' };

function formatPrice(plan: PlanPrice): string {
  return `${CURRENCY_SYMBOL[plan.currency]}${plan.amount.toFixed(2)}`;
}

export const PlanBillingScreen: React.FC = () => {
  const t = useTheme();
  const plans = usePlans();
  const summary = useSubscriptionSummary();
  const subscribe = useSubscribe();

  // Explicit choice, not inferred — no geo/IP detection exists yet (a real
  // decision still needed; see the billing recon). Defaults to USD, held
  // as real screen state so it survives re-renders while picking a plan.
  const [currency, setCurrency] = useState<BillingCurrency>('USD');
  const [pendingPlanId, setPendingPlanId] = useState<string | null>(null);
  const [unavailableMessage, setUnavailableMessage] = useState<string | null>(null);

  const plansByKey = new Map(
    (plans.data?.plans ?? []).map((p) => [`${p.tier}:${p.cadence}:${p.currency}`, p]),
  );

  const onSubscribe = (plan: PlanPrice) => {
    setUnavailableMessage(null);
    setPendingPlanId(plan.planId);
    subscribe.mutate(
      { planId: plan.planId, currency: plan.currency },
      {
        onSettled: () => setPendingPlanId(null),
        onError: (e) => {
          // MANDATORY honest state: this is the real, expected outcome today
          // (no live Stripe/Razorpay credentials configured) — never render
          // a fake success, never crash.
          if (isApiError(e) && e.code === 'PAYMENT_PROVIDER_UNAVAILABLE') {
            setUnavailableMessage(
              "Payments aren't live yet — subscribing isn't available in this build.",
            );
          } else {
            setUnavailableMessage('Something went wrong. Please try again.');
          }
        },
      },
    );
  };

  const currentPlan = summary.data?.currentPlan;
  const subscription = summary.data?.subscription ?? null;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Plan</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Your workspace's tier and billing status.
        </Text>
        <Spacer size={6} />

        <Card header={<CardHeader title="Current plan" />}>
          <HairlineRowList>
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text variant="h2">{currentPlan ? TIER_LABEL[currentPlan] : '—'}</Text>
                {subscription ? (
                  <>
                    <Spacer size={1} />
                    <Text variant="bodySm" color="secondary">
                      {STATUS_COPY[subscription.status]} · via{' '}
                      {subscription.provider === 'stripe' ? 'Stripe' : 'Razorpay'}
                    </Text>
                  </>
                ) : (
                  <>
                    <Spacer size={1} />
                    <Text variant="bodySm" color="secondary">
                      No active subscription
                    </Text>
                  </>
                )}
              </View>
            </View>
          </HairlineRowList>
        </Card>

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          CURRENCY
        </Text>
        <Spacer size={2} />
        {CURRENCIES.map((c) => (
          <React.Fragment key={c}>
            <ChoiceTile
              label={c === 'USD' ? 'US Dollar' : 'Indian Rupee'}
              description={c === 'USD' ? 'Billed via Stripe' : 'Billed via Razorpay'}
              selected={currency === c}
              onPress={() => setCurrency(c)}
            />
            <Spacer size={2} />
          </React.Fragment>
        ))}

        {unavailableMessage ? (
          <>
            <Spacer size={4} />
            <View
              style={[
                styles.banner,
                {
                  backgroundColor: t.colors.bg.elevated,
                  borderColor: t.colors.semantic.danger,
                  borderRadius: t.radius.lg,
                },
              ]}
            >
              <Icon name="TriangleAlert" color="danger" size="sm" />
              <Spacer size={2} />
              <Text variant="bodySm" color="danger" style={{ flex: 1 }}>
                {unavailableMessage}
              </Text>
            </View>
          </>
        ) : null}

        {PAID_TIERS.map((tier) => (
          <React.Fragment key={tier}>
            <Spacer size={6} />
            <Card header={<CardHeader title={TIER_LABEL[tier]} />}>
              <HairlineRowList>
                {CADENCES.map((cadence) => {
                  const plan = plansByKey.get(`${tier}:${cadence}:${currency}`);
                  return (
                    <View key={cadence} style={styles.row}>
                      <View style={{ flex: 1 }}>
                        <Text variant="body">{CADENCE_LABEL[cadence]}</Text>
                        <Spacer size={1} />
                        <Text variant="bodySm" color="secondary">
                          {plan ? formatPrice(plan) : '—'}
                        </Text>
                      </View>
                      <Button
                        label="Subscribe"
                        variant="secondary"
                        size="sm"
                        disabled={!plan}
                        loading={plan !== undefined && pendingPlanId === plan.planId}
                        onPress={() => plan && onSubscribe(plan)}
                        testID={plan ? `subscribe-${plan.planId}` : undefined}
                      />
                    </View>
                  );
                })}
              </HairlineRowList>
            </Card>
          </React.Fragment>
        ))}

        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  banner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
    borderWidth: 1,
  },
});
