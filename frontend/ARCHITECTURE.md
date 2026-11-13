# Architecture and SOLID rules

## Current state

A plain application frame with sidebar, header and blank routed pages. No dummy records or fake user identity. Runtime: main.tsx → RouterProvider → AppShell → feature page.

## Active patterns

- Component composition: AppShell contains an Outlet; features use shared UI components.
- Feature-based separation: pages live in independent folders.
- Boundary handling: application and route errors have fallback UI.

## Prepared, not connected

CaseReader is a small read-only repository interface. Its provider supports dependency injection and its hooks support loading/error/retry and stale-response suppression. No concrete repository or provider is mounted. The previous mock implementation and fixture data were removed at the user's request. The API helper is also unused.

## SOLID guidance

- S: keep frame, presentation, data access and request lifecycle separate.
- O: add feature pages inside the shell; replace data implementations behind contracts.
- L: future CaseReader implementations return CaseSummary data, null for missing IDs, reject operational failures, and avoid leaking mutable internal state.
- I: keep read, write, upload, inference and chat interfaces small and separate.
- D: data-consuming hooks depend on interfaces; future concrete implementations are injected at the composition root.

These are coding constraints, not claims that unimplemented services exist. Use small functions and composition; do not add abstractions only to increase pattern counts.

## Team rules

Develop in feature folders. Cross-review changes to shell, navigation, styles, contracts and dependencies. Keep fetch/database/model logic outside page markup. Add only real data integrations and explicit loading/empty/error states. Strategy, Factory, model Adapters and job state machines should be added only when concrete analysis workflows require them.
