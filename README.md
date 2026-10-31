# FoodSrijan Group ERP

FoodSrijan Group ERP is a multi-company operating platform for food
businesses.

## Project constitution

The approved product and architecture principles are defined in the
[Food Business ERP Project Context Bible](docs/Food_Business_ERP_Project_Context_Bible_v1.0.md).
All new implementation work must follow that document. Architectural
decisions are recorded in [docs/architecture](docs/architecture/).

## Repository areas

- `backend/` — FastAPI, SQLAlchemy, and Alembic services.
- `frontend/vaidya-vihar-frontend/` — React application.
- `docs/` — approved context, architecture decisions, specifications, and
  operational runbooks.

## Health checks

`GET /health` checks API and database connectivity. It returns HTTP 200
with `"status": "healthy"` and `"database": "available"` on success, or
HTTP 503 with `"status": "unhealthy"` and `"database": "unavailable"` if
the database connection fails. Database errors are logged server-side;
connection details are not exposed in the response.

This endpoint is a connectivity check, not a guarantee of data integrity,
PDF renderer availability, or successful authenticated business workflows.
Run backend regression tests with `../.venv/bin/python -m pytest -q` from
`backend/`. Frontend validation uses `tsc --noEmit`,
`npm test -- --watchAll=false --runInBand`, and `npm run build` from
`frontend/vaidya-vihar-frontend/`.

## Managed login credentials

Login credentials panels are available in Company **CEO & Team**, Outlet
**Manager**, and Staff **Security**. Access follows the reporting hierarchy:
Super CEO manages Company CEOs; Company CEOs manage their own outlet managers;
outlet managers manage staff in their own outlet.

Panels show the current username and password-change requirement, refreshing
every five seconds while the page is visible. Username edits and password
resets take effect immediately. Heads can generate a secure temporary password
or set one that meets the password policy. New passwords are displayed only
in the successful update response and are never recoverable afterward.
Password resets require a change at next sign-in. Credential changes revoke
existing sessions and are audited without password values. No passwords are
stored in browser storage, audit records, or real-time event payloads.

The scoped `GET .../credentials` endpoints return login metadata only.
`PATCH .../credentials` accepts a username, `reset_password: true`, or a
matching `password` / `password_confirm` pair. Credential responses disable
caching, and updates are rate-limited to 20 attempts per head per hour.
