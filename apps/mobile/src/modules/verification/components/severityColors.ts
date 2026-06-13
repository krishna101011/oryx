/* eslint-disable no-restricted-syntax -- Wave D spec fixes these exact severity
   hex values; they are intentionally NOT theme tokens (the conflict severity
   scale is a fixed semantic, identical in light and dark). */

/** severity > 0.7 */
export const SEVERITY_RED = '#EF4444';
/** 0.3 ≤ severity ≤ 0.7 */
export const SEVERITY_AMBER = '#F59E0B';
/** severity < 0.3, and the accent used for the conflict-type pill + meter fill */
export const SEVERITY_INDIGO = '#6366F1';
