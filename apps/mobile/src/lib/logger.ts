/**
 * Mobile logger.
 * Phase 1: console + in-memory ring buffer.
 * Future phase: ship to a remote sink (Sentry, Datadog, custom backend).
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
}

const BUFFER_SIZE = 200;
const buffer: LogEntry[] = [];

function push(entry: LogEntry): void {
  if (buffer.length >= BUFFER_SIZE) buffer.shift();
  buffer.push(entry);
}

function format(level: LogLevel, message: string, context?: Record<string, unknown>): string {
  const tag = `[${level.toUpperCase()}]`;
  return context ? `${tag} ${message} ${JSON.stringify(context)}` : `${tag} ${message}`;
}

export const logger = {
  debug(message: string, context?: Record<string, unknown>) {
    const entry: LogEntry = {
      level: 'debug',
      message,
      ...(context !== undefined ? { context } : {}),
      timestamp: new Date().toISOString(),
    };
    push(entry);
    if (__DEV__) console.warn(format('debug', message, context));
  },
  info(message: string, context?: Record<string, unknown>) {
    const entry: LogEntry = {
      level: 'info',
      message,
      ...(context !== undefined ? { context } : {}),
      timestamp: new Date().toISOString(),
    };
    push(entry);
    if (__DEV__) console.warn(format('info', message, context));
  },
  warn(message: string, context?: Record<string, unknown>) {
    const entry: LogEntry = {
      level: 'warn',
      message,
      ...(context !== undefined ? { context } : {}),
      timestamp: new Date().toISOString(),
    };
    push(entry);
    console.warn(format('warn', message, context));
  },
  error(message: string, context?: Record<string, unknown>) {
    const entry: LogEntry = {
      level: 'error',
      message,
      ...(context !== undefined ? { context } : {}),
      timestamp: new Date().toISOString(),
    };
    push(entry);
    console.error(format('error', message, context));
  },
  snapshot(): LogEntry[] {
    return buffer.slice();
  },
};
