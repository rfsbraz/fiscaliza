import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import AppErrorBoundary from './components/AppErrorBoundary.jsx'
import { initSentry } from './sentry.js'
// Self-hosted fonts: nothing is loaded from a font CDN.
import './assets/fonts/fonts.css'
import './index.css'

initSentry()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>,
)
