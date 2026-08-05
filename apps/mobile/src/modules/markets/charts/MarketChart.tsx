/**
 * Phase 9 Wave B — the shared MarketChart interface.
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B)
 *
 * One public component; a future screen (Wave D — Technical Analysis)
 * consumes only this and never knows which platform-specific
 * implementation renders underneath — the same provider-abstraction
 * philosophy this project already applies to backend vendors
 * (AIProvider/PaymentProvider/VideoProvider/MarketDataProvider), applied
 * here to a UI primitive: one interface, platform-specific implementations
 * behind it, callers never branch on platform themselves.
 *
 * Branches on `Platform.OS` at render time, same runtime-branching
 * convention already used by Card.tsx/WebFrame.tsx — this codebase has no
 * .web.tsx/.native.tsx platform-extension files anywhere (confirmed by
 * search before writing this), so this file follows the ONLY convention
 * that actually exists here rather than introducing a second one.
 */
import React from 'react';
import { Platform } from 'react-native';
import { MarketChartNative } from './MarketChartNative';
import { MarketChartWeb } from './MarketChartWeb';
import type { CrosshairMoveMessage, MarketChartBar, VisibleRangeChangeMessage } from './marketChartBridge';

export interface MarketChartProps {
  bars: MarketChartBar[];
  onCrosshairMove?: (message: CrosshairMoveMessage) => void;
  onVisibleRangeChange?: (message: VisibleRangeChangeMessage) => void;
  testID?: string;
}

export const MarketChart: React.FC<MarketChartProps> = (props) => {
  if (Platform.OS === 'web') return <MarketChartWeb {...props} />;
  return <MarketChartNative {...props} />;
};
