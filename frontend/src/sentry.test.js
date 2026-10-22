// Sentry error reporting. Run with `npm test` (node --test).
// Vite loads the modules as the build does; react-test-renderer runs the error boundary.
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';

const root = fileURLToPath(new URL('..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { sentryOptions } = await vite.ssrLoadModule('/src/sentry.js');
const { default: AppErrorBoundary } = await vite.ssrLoadModule('/src/components/AppErrorBoundary.jsx');

const DSN = 'https://public@o1.ingest.de.sentry.io/1';

test('without a DSN nothing is set up, so local and dev builds send nothing', () => {
  assert.equal(sentryOptions({}), null);
  assert.equal(sentryOptions({ VITE_SENTRY_DSN: '' }), null);
});

test('with a DSN it reports errors only and no personal data', () => {
  const options = sentryOptions({ VITE_SENTRY_DSN: DSN, VITE_SENTRY_ENVIRONMENT: 'preview' });
  assert.equal(options.dsn, DSN);
  assert.equal(options.environment, 'preview');
  assert.equal(options.sendDefaultPii, false);
  for (const key of ['tracesSampleRate', 'tracesSampler', 'replaysSessionSampleRate',
    'replaysOnErrorSampleRate', 'profilesSampleRate', 'integrations']) {
    assert.ok(!(key in options), `${key} is not set`);
  }
});

test('a render error shows the pt-PT fallback with a way back home', () => {
  const Boom = () => {
    throw new Error('boom');
  };
  const consoleError = console.error;
  console.error = () => {};
  let renderer;
  try {
    act(() => {
      renderer = TestRenderer.create(
        React.createElement(AppErrorBoundary, null, React.createElement(Boom)),
      );
    });
  } finally {
    console.error = consoleError;
  }
  const text = (node) => (typeof node === 'string' ? node : (node.children || []).map(text).join(''));
  const tree = renderer.root;
  assert.match(text(tree.findByType('h1')), /^Algo correu mal$/);
  const all = tree.findAll(() => true).filter((n) => typeof n.type === 'string').map((n) => text(n)).join(' ');
  assert.match(all, /Recarregue a página ou volte ao início\./);
  const home = tree.find((n) => n.type === 'a' && n.props.href === '/');
  assert.equal(text(home), 'Voltar ao início');
});
