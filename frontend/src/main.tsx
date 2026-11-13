import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './app/router'
import { ErrorBoundary } from './app/ErrorBoundary'
import { AnalysisSessionProvider } from './features/analysis/AnalysisSession'
import './styles/index.css'
import './styles/clinical.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary><AnalysisSessionProvider><RouterProvider router={router} /></AnalysisSessionProvider></ErrorBoundary>
  </React.StrictMode>,
)
