import assert from 'node:assert/strict';
import { test } from 'node:test';
import { splitParagraphs } from './paragraphs';

test('splits on a blank line into separate paragraphs', () => {
  assert.deepEqual(splitParagraphs('First paragraph.\n\nSecond paragraph.'), [
    'First paragraph.',
    'Second paragraph.',
  ]);
});

test('treats runs of extra blank lines as a single split point', () => {
  assert.deepEqual(splitParagraphs('One.\n\n\n\nTwo.'), ['One.', 'Two.']);
});

test('trims surrounding whitespace on each paragraph', () => {
  assert.deepEqual(splitParagraphs('  Padded.  \n\n  Also padded.  '), [
    'Padded.',
    'Also padded.',
  ]);
});

test('drops empty paragraphs produced by leading/trailing blank lines', () => {
  assert.deepEqual(splitParagraphs('\n\nOnly one.\n\n'), ['Only one.']);
});

test('a single-newline hard wrap stays inside its paragraph, not split', () => {
  assert.deepEqual(splitParagraphs('Line one\nLine two.'), ['Line one\nLine two.']);
});

test('empty content produces zero paragraphs', () => {
  assert.deepEqual(splitParagraphs(''), []);
  assert.deepEqual(splitParagraphs('   \n\n   '), []);
});
