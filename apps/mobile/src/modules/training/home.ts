import type { Training } from '@oryx/shared-types';

/** Academy catalog states keep network failures distinct from a confirmed empty catalog. */
export type CourseCatalogState = 'loading' | 'error' | 'empty' | 'ready';

export function courseCatalogState(
  courses: Training.CourseCatalogItem[] | undefined,
  isError: boolean,
): CourseCatalogState {
  if (courses !== undefined) return courses.length === 0 ? 'empty' : 'ready';
  if (isError) return 'error';
  return 'loading';
}

/** For progress and lesson detail, retain cached data when a background refresh fails. */
export type AcademyQueryState = 'loading' | 'error' | 'ready';

export function academyQueryState<T>(
  data: T | undefined,
  isError: boolean,
): AcademyQueryState {
  if (data !== undefined) return 'ready';
  if (isError) return 'error';
  return 'loading';
}
