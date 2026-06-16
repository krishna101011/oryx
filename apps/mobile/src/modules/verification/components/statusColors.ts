/* eslint-disable no-restricted-syntax -- Wave E fixes packet status hex values
   by spec (#6366F1 / #22C55E / #9A9A9A); the verification-status palette is a
   fixed semantic that is identical across themes. */
import type { IntelligenceStatus, ResearchPacketStatus } from '@oryx/shared-types';

const GREEN = '#22C55E';
const AMBER = '#F59E0B';
const GREY = '#9A9A9A';
const RED = '#EF4444';
const INDIGO = '#6366F1';

export function verificationStatusColor(status: IntelligenceStatus): string {
  switch (status) {
    case 'verified':
    case 'analyst_approved':
      return GREEN;
    case 'contested':
      return AMBER;
    case 'analyst_rejected':
      return RED;
    default:
      return GREY; // unverified
  }
}

export function packetStatusColor(status: ResearchPacketStatus): string {
  switch (status) {
    case 'ready':
      return GREEN;
    case 'consumed':
      return GREY;
    default:
      return INDIGO; // assembling
  }
}
