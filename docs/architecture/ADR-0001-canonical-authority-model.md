# ADR-0001: Canonical Authority Model

- **Status:** Accepted
- **Date:** 2026-09-25
- **Decision owners:** FoodSrijan Group

## Context

The ERP currently expresses authority through `User.role`,
`User.is_super_admin`, system role rows, and role assignment rows. The
overlap makes it possible for identity, capability, and tenant scope to
disagree.

## Decision

Use authenticated identity, `ProfileType`, `RoleAssignment`, explicit scope,
permissions, and policy evaluation as the canonical authority model.

`super_ceo` is the canonical system authority. `super_admin` and
`is_super_admin` remain compatibility aliases during migration. The database
enforces at most one active user with `is_super_ceo = true`.

Profile type describes a business persona. Roles describe capabilities.
Assignments are scoped to system, company, brand, branch, or department.

## Consequences

- Authorization becomes explicit and auditable.
- Existing sessions and legacy fields can continue during migration.
- New code must not use `User.role` as its sole authority source.
- A reconciliation path is required for contradictory legacy records.

## Alternatives considered

- Keep `User.role` as the sole source: rejected because it cannot represent
  scoped roles safely.
- Use only a Super CEO boolean: rejected because it does not model delegated
  company and department authority.
- Replace all legacy fields immediately: rejected because it would break
  active sessions and compatibility.

## Related ADRs

- [ADR-0002](ADR-0002-theme-resolution-precedence.md)
- [ADR-0004](ADR-0004-route-architecture.md)
