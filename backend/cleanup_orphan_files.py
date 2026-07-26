from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from sqlalchemy import text

from app.database import SessionLocal


BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"


def _normalize_to_relative_upload_path(raw_value: str) -> str | None:
    raw = (raw_value or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    candidate = parsed.path if parsed.scheme else raw

    if candidate.startswith("/api/files/"):
        candidate = candidate.replace("/api/files/", "", 1)
    elif candidate.startswith("api/files/"):
        candidate = candidate.replace("api/files/", "", 1)
    elif candidate.startswith("/uploads/"):
        candidate = candidate.replace("/uploads/", "", 1)
    elif candidate.startswith("uploads/"):
        candidate = candidate.replace("uploads/", "", 1)
    elif candidate.startswith("/"):
        candidate = candidate[1:]

    normalized = Path(candidate).as_posix().lstrip("/")
    if not normalized or normalized.startswith(".."):
        return None
    return normalized


def _table_columns(db, table_name: str) -> set[str]:
    rows = db.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def _collect_column_references(db, table_name: str, column_name: str) -> set[str]:
    references: set[str] = set()
    rows = db.execute(
        text(f"SELECT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL")
    ).scalars().all()
    for raw in rows:
        if not isinstance(raw, str):
            continue
        relative = _normalize_to_relative_upload_path(raw)
        if relative:
            references.add(relative)
    return references


def _iter_nested_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_nested_strings(nested)
        return
    if isinstance(value, list):
        for nested in value:
            yield from _iter_nested_strings(nested)


def _collect_system_setting_references(db) -> set[str]:
    references: set[str] = set()
    table_names = {row[0] for row in db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
    if "system_settings" not in table_names:
        return references

    cols = _table_columns(db, "system_settings")
    if "setting_value" not in cols:
        return references

    rows = db.execute(text("SELECT setting_value FROM system_settings WHERE setting_value IS NOT NULL")).scalars().all()
    for raw in rows:
        if not isinstance(raw, str):
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        for candidate in _iter_nested_strings(parsed):
            relative = _normalize_to_relative_upload_path(candidate)
            if relative:
                references.add(relative)
    return references


def _collect_referenced_files() -> set[str]:
    db = SessionLocal()
    try:
        references: set[str] = set()
        table_names = {row[0] for row in db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        candidate_columns = [
            ("users", "photo_url"),
            ("branches", "logo_url"),
            ("staff_profiles", "photo_path"),
            ("branches", "director_photo_url"),
        ]

        for table_name, column_name in candidate_columns:
            if table_name not in table_names:
                continue
            if column_name not in _table_columns(db, table_name):
                continue
            references.update(_collect_column_references(db, table_name, column_name))

        references.update(_collect_system_setting_references(db))
        return references
    finally:
        db.close()


def main() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    referenced = _collect_referenced_files()
    files_on_disk = {
        path.relative_to(UPLOADS_DIR).as_posix()
        for path in UPLOADS_DIR.rglob("*")
        if path.is_file()
    }
    orphaned = sorted(files_on_disk - referenced)

    deleted = 0
    for relative in orphaned:
        target = (UPLOADS_DIR / relative).resolve()
        if UPLOADS_DIR.resolve() not in target.parents:
            continue
        if target.exists():
            target.unlink()
            deleted += 1

    print(f"Referenced files: {len(referenced)}")
    print(f"Files on disk: {len(files_on_disk)}")
    print(f"Deleted orphan files: {deleted}")


if __name__ == "__main__":
    main()
