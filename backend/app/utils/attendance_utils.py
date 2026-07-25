from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont


def reverse_geocode_address(latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
    if latitude is None or longitude is None:
        return None

    query = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "lat": f"{latitude}",
            "lon": f"{longitude}",
            "zoom": "16",
            "addressdetails": "1",
        }
    )
    url = f"https://nominatim.openstreetmap.org/reverse?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VaidyaViharAttendance/1.0 (support@vaidyavihar.local)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
            display_name = (payload.get("display_name") or "").strip()
            return display_name or None
    except Exception:
        return None


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def stamp_image_with_gps(
    image_path: Path,
    latitude: Optional[float],
    longitude: Optional[float],
    clock_time: datetime,
    address: Optional[str] = None,
) -> Path:
    image = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    font = _load_font(16)

    # Convert incoming UTC/naive timestamps to local wall time for human-readable image stamps.
    if clock_time.tzinfo is None:
        local_clock_time = clock_time.replace(tzinfo=timezone.utc).astimezone()
    else:
        local_clock_time = clock_time.astimezone()

    timestamp_text = local_clock_time.strftime("%d/%m/%Y %H:%M:%S")
    latlng_text = (
        f"Lat: {latitude:.6f}, Lng: {longitude:.6f}"
        if latitude is not None and longitude is not None
        else "Lat/Lng: unavailable"
    )
    resolved_address = (address or reverse_geocode_address(latitude, longitude) or "unavailable").strip()
    if len(resolved_address) > 64:
        resolved_address = f"{resolved_address[:61]}..."
    lines = [
        f"Date & Time: {timestamp_text}",
        latlng_text,
        f"Address: {resolved_address}",
    ]

    max_width = 0
    line_height = 0
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        max_width = max(max_width, right - left)
        line_height = max(line_height, bottom - top)

    padding_x = 12
    padding_y = 10
    gap = 6
    box_width = max_width + (padding_x * 2)
    box_height = (line_height * len(lines)) + (gap * (len(lines) - 1)) + (padding_y * 2)

    # Keep a stable stamp anchor at bottom-right with safe edge padding.
    x2 = image.width - 12
    y2 = image.height - 12
    x1 = max(12, x2 - box_width)
    y1 = max(12, y2 - box_height)

    draw.rectangle((x1, y1, x2, y2), fill=(0, 0, 0, 165))

    text_x = x1 + padding_x
    text_y = y1 + padding_y
    for line in lines:
        draw.text((text_x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_height + gap

    stamped_path = image_path.with_name(f"stamped_{image_path.stem}.jpg")
    stamped_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(stamped_path, format="JPEG", quality=92)
    return stamped_path


def stamp_attendance_image(
    source_path: Path,
    destination_path: Path,
    capture_time: datetime,
    latitude: Optional[float],
    longitude: Optional[float],
) -> None:
    stamped_path = stamp_image_with_gps(
        image_path=source_path,
        latitude=latitude,
        longitude=longitude,
        clock_time=capture_time,
    )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if stamped_path != destination_path:
        stamped_path.replace(destination_path)
