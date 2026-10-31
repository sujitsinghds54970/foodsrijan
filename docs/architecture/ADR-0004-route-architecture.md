# ADR-0004: Route Architecture

- **Status:** Accepted
- **Date:** 2026-09-25
- **Decision owners:** FoodSrijan Group

## Context

The former Super CEO surface parsed the pathname manually and rendered all
tabs from one large component. This made direct navigation, code splitting,
route guards, and future tab-specific data loading fragile.

## Decision

Use React Router v6 nested routes. A persistent `SuperCEOWorkspace` owns the
access guard, theme provider, shell, sidebar, topbar, command palette, and
`Outlet`. Tab groups are lazy-loaded route modules.

Canonical paths use `/super-ceo/*`. Existing `/super-admin/*` paths remain
client-side compatibility redirects for at least 90 days or two release
cycles, followed by one read-only deprecation cycle.

## Consequences

- Direct URLs are bookmarkable and route-driven.
- Tab groups can be code-split.
- Guards can be applied at workspace and tab level.
- The former monolithic page becomes a compatibility entry point.

## Alternatives considered

- Continue manual pathname parsing: rejected because it duplicates router
  behavior and weakens route-level loading/guards.
- One route per component without a persistent layout: rejected because it
  would duplicate executive chrome and state.
- Replace legacy routes immediately: rejected because existing bookmarks and
  integrations must continue.

## Related ADRs

- [ADR-0001](ADR-0001-canonical-authority-model.md)
