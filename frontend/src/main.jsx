import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import AppErrorBoundary from './components/AppErrorBoundary.jsx'
import { initSentry } from './sentry.js'
// Self-hosted fonts: nothing is loaded from a font CDN.
import './assets/fonts/fonts.css'
import './index.css'

initSentry()

// TEMPORARY (#178): ?sentry-test=1 throws while rendering so the preview can prove an error
// reaches Sentry and show the fallback.
const SentryTestTrigger = () => {
  if (new URLSearchParams(window.location.search).get('sentry-test') === '1') {
    throw new Error('Fiscaliza Sentry test error (temporary preview trigger)')
  }
  return null
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <SentryTestTrigger />
      <App />
    </AppErrorBoundary>
  </React.StrictMode>,
)
