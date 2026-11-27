import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { academyQueryState, courseCatalogState } from './home';

const read = (rel: string): string =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8');

test('courseCatalogState distinguishes loading, error, confirmed-empty and ready', () => {
  assert.equal(courseCatalogState(undefined, false), 'loading');
  assert.equal(courseCatalogState(undefined, true), 'error');
  assert.equal(courseCatalogState([], false), 'empty');
  assert.equal(courseCatalogState([{ id: 'course-1' } as never], false), 'ready');
});

test('cached Academy catalog remains visible during a background refresh error', () => {
  assert.equal(courseCatalogState([{ id: 'course-1' } as never], true), 'ready');
  assert.equal(courseCatalogState([], true), 'empty');
});

test('academyQueryState distinguishes loading, error and available data', () => {
  assert.equal(academyQueryState(undefined, false), 'loading');
  assert.equal(academyQueryState(undefined, true), 'error');
  assert.equal(academyQueryState({ lessons: [] }, false), 'ready');
});

test('cached Academy data remains usable when a background refresh fails', () => {
  assert.equal(academyQueryState({ lessons: [] }, true), 'ready');
});

test('course progress requests are enabled only while its enrolled course is expanded', () => {
  const hook = read('./hooks/useTraining.ts');
  const screen = read('./screens/AcademyHomeScreen.tsx');
  assert.ok(hook.includes('export function useCourseProgress(courseId: string, enabled = true)'));
  assert.ok(hook.includes('    enabled,'));
  assert.ok(screen.includes('useCourseProgress(course.id, expanded)'));
});

test('Academy catalog, progress, lesson and completion failures offer recovery', () => {
  const academy = read('./screens/AcademyHomeScreen.tsx');
  const lesson = read('./screens/LessonViewerScreen.tsx');
  assert.ok(academy.includes('catalog.refetch()'));
  assert.ok(academy.includes('progress.refetch()'));
  assert.ok(lesson.includes('lesson.refetch()'));
  assert.ok(lesson.includes('complete.isError'));
});
