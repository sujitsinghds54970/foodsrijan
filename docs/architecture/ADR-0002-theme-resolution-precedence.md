# ADR-0002: Theme Resolution Precedence

- **Status:** Accepted
- **Date:** 2026-09-25
- **Decision owners:** FoodSrijan Group

## Context

The Software UI capability needs profile-aware, multi-company theming without
allowing a tenant or user override to escape its authorized boundary.

## Decision

Resolve themes in this order:

```text
department > branch > role > brand > company > profile type > system default
```

User-specific overrides are intentionally excluded from the first release.
An assignment must match the active profile type, workspace scope, and
published lifecycle state. More-specific assignments override less-specific
assignments. Missing or invalid themes fall back to the nearest valid parent
and then the platform fallback.

Built-in presets are immutable. Custom themes may be created by cloning a
preset. Production changes require explicit Publish and create immutable
version snapshots.

## Consequences

- Visual governance is predictable.
- Individual users cannot bypass approved standards in v1.
- Company and brand isolation is enforceable through the scope resolver.
- Theme publishing requires version, audit, and cache invalidation support.

## Alternatives considered

- User-first overrides: rejected for the first release because they weaken
  governance.
- Single global theme: rejected because it cannot represent multi-company
  branding.
- Mutable theme rows without versions: rejected because rollback and audit
  requirements would be impossible to satisfy reliably.

## Related ADRs

- [ADR-0001](ADR-0001-canonical-authority-model.md)
- [ADR-0003](ADR-0003-realtime-event-contract.md)
