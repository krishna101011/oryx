/* eslint-disable no-restricted-syntax -- Phase 5 Wave A fixes draft status +
   format hex values by spec (blueprint §11.6). These are fixed semantic
   palettes, identical across themes; the only place raw hex is allowed. */
import type { ContentFormat, DraftStatus } from '@oryx/shared-types';

const GREY = '#4E5D6C';
const SECONDARY = '#8B95A5';
const AMBER = '#F59E0B';
const GREEN = '#22C55E';
const INDIGO = '#6366F1';
const TEAL = '#00D4C8';
const RED = '#EF4444';
const BLUE = '#60A5FA';
const VIOLET = '#9B5DE5';

export function draftStatusColor(status: DraftStatus): string {
  switch (status) {
    case 'in_review':
    case 'changes_requested':
      return AMBER;
    case 'approved':
      return GREEN;
    case 'scheduled':
      return INDIGO;
    case 'published':
      return TEAL;
    case 'rejected':
      return RED;
    default:
      return GREY; // draft, archived
  }
}

export function formatColor(format: ContentFormat): string {
  switch (format) {
    case 'tweet_thread':
      return BLUE;
    case 'linkedin_post':
      return INDIGO;
    case 'newsletter_section':
      return VIOLET;
    case 'article':
      return TEAL;
    case 'report_summary':
      return GREY;
    default:
      return SECONDARY; // custom
  }
}

export const DRAFT_STATUS_LABEL: Record<DraftStatus, string> = {
  draft: 'Draft',
  in_review: 'In review',
  changes_requested: 'Changes requested',
  approved: 'Approved',
  scheduled: 'Scheduled',
  published: 'Published',
  rejected: 'Rejected',
  archived: 'Archived',
};

export const FORMAT_LABEL: Record<ContentFormat, string> = {
  tweet_thread: 'Tweet',
  linkedin_post: 'LinkedIn',
  newsletter_section: 'Newsletter',
  article: 'Article',
  report_summary: 'Report',
  custom: 'Custom',
};

export const CONTENT_FORMATS: ContentFormat[] = [
  'article',
  'tweet_thread',
  'linkedin_post',
  'newsletter_section',
  'report_summary',
  'custom',
];
