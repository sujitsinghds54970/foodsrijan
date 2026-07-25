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
    
    # Get address from parameter or reverse geocode, ensure it's truncated properly
    resolved_address = (address or reverse_geocode_address(latitude, longitude) or "Location unavailable").strip()
    if len(resolved_address) > 60:
        resolved_address = f"{resolved_address[:57]}..."
    
    lines = [
        f"Time: {timestamp_text}",
        latlng_text,
        f"Location: {resolved_address}",
    ]

    # Calculate text dimensions for the overlay box
    max_width = 0
    line_height = 0
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        max_width = max(max_width, right - left)
        line_height = max(line_height, bottom - top)

    # Padding around the text inside the overlay box
    padding_x = 15
    padding_y = 12
    gap = 5
    
    # Calculate box dimensions to fit text snugly
    box_width = max_width + (padding_x * 2)
    box_height = (line_height * len(lines)) + (gap * (len(lines) - 1)) + (padding_y * 2)

    # Position stamp at bottom-right corner with 15px from edges
    edge_offset = 15
    x2 = image.width - edge_offset
    y2 = image.height - edge_offset
    x1 = x2 - box_width
    y1 = y2 - box_height
    
    # Ensure box doesn't go off the left/top edges
    if x1 < edge_offset:
        x1 = edge_offset
        x2 = x1 + box_width
    if y1 < edge_offset:
        y1 = edge_offset
        y2 = y1 + box_height

    # Draw semi-transparent rounded rectangle background (0.6 opacity ≈ 153 in RGBA)
    # Using rectangle with rounded corners via multiple draws or just rectangle with rounded effect
    corner_radius = 8
    try:
        # Try to use rounded_rectangle if available (Pillow >= 8.2.0)
        draw.rounded_rectangle(
            [(x1, y1), (x2, y2)],
            radius=corner_radius,
            fill=(0, 0, 0, 153)  # Semi-transparent black (60% opacity)
        )
    except AttributeError:
        # Fallback for older Pillow versions: just use regular rectangle
        draw.rectangle([(x1, y1), (x2, y2)], fill=(0, 0, 0, 153))

    # Draw text lines with white color
    text_x = x1 + padding_x
    text_y = y1 + padding_y
    for line in lines:
        draw.text((text_x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_height + gap

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
