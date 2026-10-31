# ADR-0003: Realtime Event Contract

- **Status:** Accepted
- **Date:** 2026-09-25
- **Decision owners:** FoodSrijan Group

## Context

Published theme changes should reach connected users within seconds. The
existing application has WebSocket infrastructure, but no versioned theme
event semantics or tenant-aware subscription contract.

## Decision

Use versioned WebSocket events with at-least-once delivery and idempotent
client application by `version_id`. Publish events only for explicit
production changes, not every draft editor keystroke.

Initial event names include:

- `theme.published`
- `theme.assigned`
- `theme.rolled_back`
- `profile_type.created`
- `profile_type.updated`

Each event carries an event ID, event version, actor, tenant scope, resource
identity, and published version. The server authorizes subscriptions; the
client cannot choose an arbitrary tenant channel.

SSE or polling is the fallback when WebSocket connectivity is unavailable.

## Consequences

- Duplicate and out-of-order events are safe to process.
- Theme payloads can be fetched by version rather than broadcast in full.
- Scope authorization must be applied at connection and subscription time.
- Draft editing remains local and avoids event storms.

## Alternatives considered

- Exactly-once delivery: rejected as disproportionate to the requirement.
- Broadcast full token documents: rejected because payloads become large and
  stale events are harder to reconcile.
- Polling only: rejected because it adds avoidable latency.

## Related ADRs

- [ADR-0002](ADR-0002-theme-resolution-precedence.md)
