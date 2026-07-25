from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont


def reverse_geocode(latitude: Optional[float], longitude: Optional[float]) -> str:
    if latitude is None or longitude is None:
        return "Location unavailable"

    query = urllib.parse.urlencode({
        "format": "jsonv2",
        "lat": f"{latitude}",
        "lon": f"{longitude}",
        "zoom": "16",
        "addressdetails": "1",
    })
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
            display = (payload.get("display_name") or "").strip()
            if display:
                return display
    except Exception:
        pass

    return "Address unavailable"


def stamp_selfie_with_gps(
    source_path: Path,
    destination_path: Path,
    capture_time: datetime,
    latitude: Optional[float],
    longitude: Optional[float],
) -> None:
    address = reverse_geocode(latitude, longitude)
    dt_label = capture_time.strftime("%d/%m/%Y, %H:%M:%S")
    coord_label = (
        f"{latitude:.6f}, {longitude:.6f}" if latitude is not None and longitude is not None else "Coordinates unavailable"
    )

    image = Image.open(source_path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    def text_width(value: str, font_obj) -> int:
        bbox = draw.textbbox((0, 0), value, font=font_obj)
        return bbox[2] - bbox[0]

    lines = [
        dt_label,
        coord_label,
        address,
    ]

    line_height = 16
    panel_padding = 12
    icon_size = 26
    max_text_width = max(text_width(line, font) for line in lines)
    panel_width = int(max_text_width + panel_padding * 2 + icon_size + 16)
    panel_height = int(panel_padding * 2 + line_height * len(lines) + 6)

    x2 = image.width - 12
    y2 = image.height - 12
    x1 = max(10, x2 - panel_width)
    y1 = max(10, y2 - panel_height)

    # Shadow behind the stamp for readability.
    draw.rounded_rectangle((x1 + 2, y1 + 2, x2 + 2, y2 + 2), radius=14, fill=(0, 0, 0, 70))
    draw.rounded_rectangle((x1, y1, x2, y2), radius=14, fill=(10, 15, 25, 190), outline=(255, 255, 255, 60), width=2)

    icon_x1 = x1 + panel_padding
    icon_y1 = y1 + panel_padding
    icon_x2 = icon_x1 + icon_size
    icon_y2 = icon_y1 + icon_size
    draw.rounded_rectangle((icon_x1, icon_y1, icon_x2, icon_y2), radius=8, fill=(59, 130, 246, 240))
    draw.polygon(
        [
            (icon_x1 + 8, icon_y1 + 6),
            (icon_x1 + 18, icon_y1 + 6),
            (icon_x1 + 14, icon_y1 + 14),
            (icon_x1 + 13, icon_y1 + 21),
            (icon_x1 + 12, icon_y1 + 14),
        ],
        fill=(255, 255, 255, 255),
    )
    draw.ellipse((icon_x1 + 10, icon_y1 + 9, icon_x1 + 14, icon_y1 + 13), fill=(59, 130, 246, 255))

    text_x = icon_x2 + 8
    text_y = y1 + panel_padding
    for idx, line in enumerate(lines):
        current_font = font if idx == 0 else small_font
        draw.text((text_x, text_y), line, font=current_font, fill=(255, 255, 255, 255))
        text_y += line_height

    map_badge_text = "MAP"
    badge_width = text_width(map_badge_text, small_font) + 18
    badge_x2 = x2 - panel_padding
    badge_x1 = badge_x2 - badge_width
    badge_y1 = y1 + panel_padding
    badge_y2 = badge_y1 + 24
    draw.rounded_rectangle((badge_x1, badge_y1, badge_x2, badge_y2), radius=12, fill=(34, 197, 94, 220))
    draw.text((badge_x1 + 10, badge_y1 + 4), map_badge_text, font=small_font, fill=(255, 255, 255, 255))

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination_path, format="JPEG", quality=90)
