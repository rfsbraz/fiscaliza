import * as Sentry from '@sentry/react';

/**
 * Sentry error reporting: errors only, so no tracing, session replay or profiling, and no
 * personal data (sendDefaultPii: false). The DSN is public and comes from the build env
 * (VITE_SENTRY_DSN in .github/workflows/deploy.yml). Without one, as in local and dev builds,
 * Sentry is not set up and nothing is sent.
 */
export function sentryOptions(env) {
  const dsn = env.VITE_SENTRY_DSN;
  if (!dsn) return null;
  return {
    dsn,
    environment: env.VITE_SENTRY_ENVIRONMENT || 'production',
    sendDefaultPii: false,
  };
}

export function initSentry(env = import.meta.env) {
  const options = sentryOptions(env);
  if (options) Sentry.init(options);
  return Boolean(options);
}
