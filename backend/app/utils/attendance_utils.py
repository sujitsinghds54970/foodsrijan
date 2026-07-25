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
        print(f"⚠️ [REVERSE_GEOCODE] Missing coordinates: lat={latitude}, lng={longitude}")
        return None

    try:
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
        print(f"🌍 [REVERSE_GEOCODE] Querying: {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VaidyaViharAttendance/1.0 (support@vaidyavihar.local)",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            display_name = (payload.get("display_name") or "").strip()
            if display_name:
                print(f"✅ [REVERSE_GEOCODE] Address found: {display_name}")
                return display_name
            else:
                print(f"⚠️ [REVERSE_GEOCODE] Empty response from nominatim")
                return None
    except urllib.error.URLError as e:
        print(f"❌ [REVERSE_GEOCODE] Network error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ [REVERSE_GEOCODE] JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"❌ [REVERSE_GEOCODE] Unexpected error: {e}")
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
    font = _load_font(18)

    # Convert incoming UTC/naive timestamps to local wall time for human-readable image stamps.
    if clock_time.tzinfo is None:
        local_clock_time = clock_time.replace(tzinfo=timezone.utc).astimezone()
    else:
        local_clock_time = clock_time.astimezone()

    # Format timestamp correctly with proper date and time format: DD/MM/YYYY HH:MM:SS
    timestamp_text = local_clock_time.strftime("%d/%m/%Y %H:%M:%S")
    
    # Format latitude and longitude properly with 6 decimal places
    latlng_text = (
        f"GPS: {latitude:.6f}°N, {longitude:.6f}°E"
        if latitude is not None and longitude is not None
        else "GPS: Unavailable"
    )
    
    # Get address from parameter or reverse geocode
    if address:
        resolved_address = address.strip()
    elif latitude is not None and longitude is not None:
        resolved_address = reverse_geocode_address(latitude, longitude)
        if not resolved_address:
            # If reverse geocoding fails, use raw coordinates instead of "Location unavailable"
            resolved_address = f"Lat: {latitude:.6f}, Lng: {longitude:.6f}"
    else:
        resolved_address = "Location unavailable"
    
    # Truncate if too long
    if len(resolved_address) > 60:
        resolved_address = f"{resolved_address[:57]}..."
    
    lines = [
        f"Time: {timestamp_text}",
        latlng_text,
        f"Location: {resolved_address}",
    ]

    # Measure the full multi-line block so the box hugs the text closely.
    block_text = "\n".join(lines)
    try:
        text_left, text_top, text_right, text_bottom = draw.multiline_textbbox(
            (0, 0),
            block_text,
            font=font,
            spacing=4,
        )
        text_width = text_right - text_left
        text_height = text_bottom - text_top
    except AttributeError:
        widths = []
        heights = []
        for line in lines:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            widths.append(right - left)
            heights.append(bottom - top)
        text_width = max(widths) if widths else 0
        text_height = sum(heights) + (4 * (len(lines) - 1))

    padding = 15
    box_width = text_width + 30
    box_height = text_height + 30

    x_start = image.width - box_width - 20
    y_start = image.height - box_height - 20
    if x_start < 0 or y_start < 0:
        x_start, y_start = 10, 10

    corner_radius = 10
    try:
        draw.rounded_rectangle(
            [(x_start, y_start), (x_start + box_width, y_start + box_height)],
            radius=corner_radius,
            fill=(0, 0, 0, 140),
        )
    except AttributeError:
        draw.rectangle(
            [(x_start, y_start), (x_start + box_width, y_start + box_height)],
            fill=(0, 0, 0, 140),
        )

    draw.multiline_text(
        (x_start + padding, y_start + padding),
        block_text,
        font=font,
        fill="white",
        spacing=4,
    )

    # Save stamped image to the same directory
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
