---
title: Food Business ERP Project Context Bible
version: 1.0.0
status: approved
owner: FoodSrijan Group
last_updated: 2026-09-25
---

# Food Business ERP Project Context Bible

## 1. Purpose and authority

This document is the constitutional source of truth for the FoodSrijan Group
Food Business ERP. It defines the product vocabulary, business hierarchy,
authority principles, tenancy rules, and architectural constraints that govern
new work.

When implementation conflicts with this document, the conflict must be
recorded and resolved explicitly. New features must not silently introduce a
second authority model, tenant boundary, or terminology system.

Detailed implementation specifications belong in `docs/specifications/`.
Architectural decisions belong in `docs/architecture/`.

## 2. Product mission

FoodSrijan Group ERP is a multi-company operating platform for food businesses.
It provides a unified view of companies, brands, branches, departments,
people, customers, suppliers, investors, finance, supply chain, governance,
and operational intelligence.

The Super CEO is the highest authority in the platform and uses the Super CEO
workspace as the group command center.

## 3. Business hierarchy

The authoritative business hierarchy is:

```text
FoodSrijan Group / System
  └── Company
       └── Brand
            └── Branch
                 └── Department
```

Every company-scoped, brand-scoped, branch-scoped, or department-scoped
operation must be evaluated against this hierarchy.

## 4. Canonical authority principles

Authority is determined by authenticated identity, profile type, role
assignment, scope, permissions, and applicable policies.

The canonical primitives are:

- `User` for identity.
- `ProfileType` for the business persona and UI identity.
- `Role` for a capability bundle.
- `Permission` for an atomic capability.
- `RoleAssignment` for a user's capability within a scope.
- Scope hierarchy: system, company, brand, branch, department.
- `is_super_ceo` as the constrained system-level authority marker.

There is exactly one active Super CEO. The database must enforce at most one
active user with `is_super_ceo = true`.

The legacy `User.role`, `User.is_super_admin`, the `super_admin` role alias,
and `/api/super-admin/*` routes remain during migration compatibility. They
are not the long-term source of truth for new authorization decisions.

## 5. Super CEO authority

The Super CEO may view and govern the entire group. Mutations against a
company, brand, branch, or department must still identify an explicit target
scope and must be recorded in the audit trail.

Super CEO publishing and configuration actions are self-approved because the
Super CEO is the highest authority. Every publish action must log:

- Actor.
- Timestamp.
- Resource and version.
- Diff summary.
- Scope affected.

## 6. Profile types

The platform supports:

1. Global system profile types seeded by the platform.
2. Company or brand custom profile types created by authorized users.

System profile types are immutable in identity: they cannot be deleted or
renamed. Custom profile types can be created, archived, and managed.

Initial system profile types may include Super CEO, Company CEO, Department
Head, Kitchen Manager, Chef, Customer, Supplier, Investor, and other approved
business personas. The stable machine key is the identity; display labels may
be localized later.

Profile type and security role are distinct concepts:

- Profile type answers who a person is in the business.
- Role answers what the person may do.

## 7. Multi-company and tenant isolation

Users may belong to multiple companies. The active workspace context must be
explicit. Company, brand, branch, department, and theme data must not leak
across tenant boundaries.

The scope hierarchy is restrictive: a lower scope cannot expand authority
beyond its parent scope.

Theme resolution supports system defaults and approved overrides at role,
department, branch, brand, and company scopes. User-specific theme overrides
are not part of the first implementation.

## 8. Software UI and design tokens

The Software UI area is the Super CEO's governed theme-management center.
Themes are persisted, versioned, validated, audited, and applied through CSS
variables.

Theme changes follow these rules:

- Draft changes remain local to the editor.
- Every production change requires explicit Publish.
- Built-in presets are immutable.
- A preset may be cloned into a custom theme.
- Published versions are immutable snapshots.
- Rollback creates a new version from a historical snapshot.
- Invalid or inaccessible themes fall back to the last known-good theme and
  then the platform default.

Design tokens use three layers:

```text
Raw tokens → Semantic tokens → Component tokens
```

Published themes must validate required token structure, references, value
ranges, and accessibility contrast. Normal text targets WCAG AA contrast of
4.5:1; large text and user-interface controls target 3:1.

## 9. Executive workspace principles

The Super CEO workspace is a tab-based command center organized into:

- Command
- People
- Business
- Operations
- Governance
- System

The System group includes Software UI. The workspace uses nested routes,
lazy-loaded tab content, explicit scope context, keyboard-accessible command
navigation, responsive layouts, and meaningful data density.

The Company CEO profile page is outside the scope of the Super CEO
transformation and must not be modified by this phase.

## 10. Terminology policy

New Super CEO workspace code uses domain-neutral terminology:

- business
- company
- brand
- profile type
- workspace
- theme
- scope
- executive insight

Diagnostic-era terminology such as VaidyaVihar, patient, doctor, and LIS is
not opportunistically renamed in this phase. Product-wide terminology
migration is a separate initiative.

## 11. Compatibility and migration

Migration must be additive and non-breaking:

- Preserve legacy user fields.
- Preserve legacy API aliases.
- Accept existing JWT role claims during transition.
- Normalize legacy `super_admin` authority to canonical `super_ceo`.
- Keep `/api/super-admin/*` active for at least 90 days or two release cycles,
  whichever is longer.
- After that period, legacy routes become read-only for one additional cycle
  before removal, subject to usage review.

SQLite is supported for local development. PostgreSQL JSONB is the production
target. SQLAlchemy JSON models and additive migrations must remain portable
between both paths.

## 12. Security, audit, and realtime principles

Authorization is enforced on the backend even when the frontend has route
guards. Sensitive mutations require explicit scope validation and audit
logging.

Theme realtime delivery uses versioned, idempotent events with at-least-once
delivery. Published changes should reach connected clients within seconds.
WebSocket is preferred; SSE or polling provides a fallback.

Clients must never be able to subscribe to a tenant scope that the server has
not authorized.

## 13. Amendments and later volumes

This Bible uses semantic versioning:

- Patch: clarification with no behavior change.
- Minor: additive principle or domain clarification.
- Major: authority, tenancy, or business hierarchy change.

Amendments require an amendment record, rationale, affected systems,
approving authority, and effective date.

Detailed material should be added as later volumes under:

```text
docs/architecture/
docs/specifications/
docs/operations/
```

## 14. Glossary

| Term | Meaning |
|---|---|
| Super CEO | The single highest system-level authority |
| Company | A tenant-level operating business |
| Brand | A company-owned commercial identity |
| Branch | A physical or operational business location |
| Department | An organizational unit within a company |
| Profile type | A business persona and UI identity |
| Role | A set of security capabilities |
| Scope | The business boundary in which authority applies |
| Theme | A versioned design-token configuration |
| Preset | An immutable built-in theme template |
| Workspace | The active company/brand context selected by a user |
