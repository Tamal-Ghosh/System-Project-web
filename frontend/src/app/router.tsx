import { createHashRouter, Navigate, useRouteError } from 'react-router-dom'
import { AppShell } from './AppShell'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { NewCasePage } from '../features/cases/NewCasePage'
import { WorkspacePage } from '../features/workspace/WorkspacePage'
import { ReviewsPage } from '../features/reviews/ReviewsPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { ButtonLink } from '../components/ui/Button'
import { AnalysisPage } from '../features/analysis/AnalysisPage'
import { ReportsPage } from '../features/reports/ReportsPage'
import { HelpPage } from '../features/help/HelpPage'

function NotFound() { return <div className="fatal-error"><h1>Page not found</h1><p>This page is not part of the shared base.</p><ButtonLink to="/dashboard">Return to dashboard</ButtonLink></div> }
function RouteError() { useRouteError(); return <div className="fatal-error"><h1>This page could not load</h1><p>Return to the dashboard and try again.</p><ButtonLink to="/dashboard">Return to dashboard</ButtonLink></div> }

export const router = createHashRouter([
  { element: <AppShell />, children: [
    { index: true, element: <Navigate to="/dashboard" replace /> },
    { path: 'dashboard', element: <DashboardPage />, errorElement: <RouteError /> },
    { path: 'cases', element: <Navigate to="/dashboard" replace /> },
    { path: 'cases/new', element: <NewCasePage />, errorElement: <RouteError /> },
    { path: 'cases/:caseId', element: <WorkspacePage />, errorElement: <RouteError /> },
    { path: 'reviews', element: <ReviewsPage /> },
    { path: 'analysis', element: <AnalysisPage /> },
    { path: 'assistant', element: <Navigate to="/analysis" replace /> },
    { path: 'reports', element: <ReportsPage /> },
    { path: 'help', element: <HelpPage /> },
    { path: 'evidence', element: <Navigate to="/analysis?module=validation" replace /> },
    { path: 'settings', element: <SettingsPage /> },
    { path: 'foundation', element: <Navigate to="/dashboard" replace /> },
    { path: '*', element: <NotFound /> },
  ] },
])
