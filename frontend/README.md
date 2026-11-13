# DermaScope — shared frontend frame

React + TypeScript + Vite. White theme, persistent sidebar/header and blank feature pages. No dummy records, demo profile, sample images, metrics or simulated functionality.

## Run

From this folder, run `npm ci` and `npm run dev`. Requires Node 22.12+ or a compatible newer supported Node version. The local `.npmrc` keeps cache on this drive.

Checks: `npm run typecheck` and `npm run build`.

## Extend the frame

- `src/app/AppShell.tsx`: sidebar, header, mobile navigation and content Outlet.
- `src/app/router.tsx`: page routes; `/foundation` redirects to cases.
- `src/app/navigation.ts`: shared navigation registry.
- `src/components/ui`: reusable components.
- `src/styles/index.css`: white theme and responsive styling.
- `src/features`: separate, blank feature pages for each contributor.
- `src/contracts`: future shared API types.

Current routes: `/cases`, `/cases/new`, `/cases/:caseId`, `/reviews`, `/evidence`, `/settings`.

CaseReader, provider and hooks are unconnected extension points. No provider is mounted, no data is seeded and no API calls run. Inject a real implementation when backend integration is ready. No authentication, authorization or clinical functionality is implemented.

Read ARCHITECTURE.md for team coding rules. Commit package-lock.json, not node_modules, dist or local caches.

## Floating assistant frame

The bottom-right chat button toggles a non-modal chat window; close button and Escape return focus to the launcher. It has no messages or connected send service. The sidebar has no AI Assistant entry. Case routes show their current context; navigation resets the chat frame to avoid carrying context across pages.

## Navigation update

Dashboard is the landing page (`/dashboard`); legacy `/cases` redirects there. Analysis includes Result, Explain and More analysis navigation. More analysis provides empty module frames for agreement, uncertainty, crop sensitivity, stability, prediction sets and input quality. No results are generated. Model-level validation remains under Model evidence.

## Current workflow (supersedes the earlier navigation notes)

Dashboard now contains image upload, ROI preparation, classification, XAI and case-level uncertainty. `/analysis` is a separate advanced-analysis page for calibration, validation, model comparison, crop sensitivity, stability, conformal sets, segmentation and subgroup/external evidence. `/evidence` redirects to its validation module; its separate sidebar entry has been removed.

AnalysisSessionProvider owns the uploaded image and committed region, undo history, zoom and preview mode. These remain in memory during route navigation; a full refresh or closing the app resets them. No patient data is written to localStorage. Advanced pages show the current image context and unavailable states, not fabricated metrics. The floating assistant remains separate from navigation.

The untouched pre-redesign backup is previewed in `../backup-preview` on port 5174, using a node_modules junction to the installed dependencies. Its source files remain separate from this frontend on port 5173.
