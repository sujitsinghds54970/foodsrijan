from __future__ import annotations

import io
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED_CATEGORIES = {
    "profile-photos",
    "cover-photos",
    "company-logos",
    "company-banners",
    "staff-photos",
}
ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _reject_unsafe_svg(content: bytes) -> None:
    text = content.decode("utf-8", errors="ignore")
    if re.search(r"<\s*script\b|\bonload\s*=", text, flags=re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SVG contains unsafe executable content",
        )


def _save_raster_variants(content: bytes, target: Path, extension: str) -> None:
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image",
        ) from exc

    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    output_format = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[
        extension.removeprefix(".")
    ]
    save_options = {"quality": 85, "optimize": True} if output_format in {"JPEG", "WEBP"} else {"optimize": True}

    web = image.copy()
    web.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
    web.save(target.with_name(f"{target.stem}-web{extension}"), output_format, **save_options)

    thumb = ImageOps.fit(image, (200, 200), Image.Resampling.LANCZOS)
    thumb.save(target.with_name(f"{target.stem}-thumb{extension}"), output_format, **save_options)


async def save_upload(file: UploadFile, category: str, sub_id: int | str) -> dict[str, str | int]:
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Unsupported upload category")
    mime = (file.content_type or "").lower()
    extension = ALLOWED_MIME_TYPES.get(mime)
    if extension is None:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB limit")
    if mime == "image/svg+xml":
        _reject_unsafe_svg(content)

    folder = UPLOAD_ROOT / category / str(sub_id)
    folder.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex
    target = folder / f"{stem}{extension}"
    target.write_bytes(content)

    if mime == "image/svg+xml":
        target.with_name(f"{stem}-web{extension}").write_bytes(content)
        target.with_name(f"{stem}-thumb{extension}").write_bytes(content)
    else:
        _save_raster_variants(content, target, extension)

    return {
        "url": f"/uploads/{category}/{sub_id}/{target.name}",
        "filename": target.name,
        "size": len(content),
        "mime": mime,
    }
