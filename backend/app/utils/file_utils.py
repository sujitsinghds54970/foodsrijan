import os
import secrets
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import UploadFile


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = BASE_DIR / "uploads"


def _normalize_relative_upload_path(raw_path: str) -> Optional[str]:
    raw = (raw_path or "").strip()
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


def storage_relative_path_from_public_url(url_path: str) -> Optional[str]:
    return _normalize_relative_upload_path(url_path)


def replace_file(old_url_path: Optional[str], new_file_object: UploadFile, upload_subdir: str) -> str:
    relative_old_path = _normalize_relative_upload_path(old_url_path or "")
    if relative_old_path:
        old_abs_path = (UPLOADS_DIR / relative_old_path).resolve()
        uploads_root = UPLOADS_DIR.resolve()
        if uploads_root in old_abs_path.parents and os.path.exists(old_abs_path):
            os.remove(old_abs_path)

    source_name = (new_file_object.filename or "").strip() or "upload.bin"
    extension = Path(source_name).suffix.lower() or ".bin"
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico"}:
        extension = ".bin"
    safe_subdir = Path(upload_subdir.strip("/")).as_posix()
    target_dir = (UPLOADS_DIR / safe_subdir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"upload_{secrets.token_hex(16)}{extension}"
    new_abs_path = target_dir / filename
    with new_abs_path.open("wb") as output:
        output.write(new_file_object.file.read())

    relative_new_path = f"{safe_subdir}/{filename}".strip("/")
    return f"http://localhost:8000/api/files/{relative_new_path}"
