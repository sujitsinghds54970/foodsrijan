from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
from typing import Optional
import json
import textwrap
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont
import requests


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
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _is_valid_coordinate_pair(latitude: Optional[float], longitude: Optional[float]) -> bool:
    if latitude is None or longitude is None:
        return False
    return abs(latitude) > 0 and abs(longitude) > 0


def fetch_map_thumbnail(latitude: float, longitude: float, size: int = 100) -> Optional[Image.Image]:
    google_maps_key = (os.getenv("GOOGLE_STATIC_MAPS_API_KEY") or "").strip()
    if not google_maps_key:
        print("⚠️ [MAP_THUMBNAIL] GOOGLE_STATIC_MAPS_API_KEY not configured")
        return None

    request_size = max(64, min(size * 2, 640))
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/staticmap",
            params={
                "center": f"{latitude},{longitude}",
                "zoom": "15",
                "size": f"{request_size}x{request_size}",
                "maptype": "roadmap",
                "markers": f"color:red|{latitude},{longitude}",
                "key": google_maps_key,
            },
            timeout=8,
        )
        response.raise_for_status()
        map_image = Image.open(BytesIO(response.content)).convert("RGB")
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        return map_image.resize((size, size), resampling)
    except requests.RequestException as error:
        print(f"❌ [MAP_THUMBNAIL] Request failed: {error}")
    except (OSError, ValueError) as error:
        print(f"❌ [MAP_THUMBNAIL] Failed to parse static map image: {error}")
    return None


def _build_map_fallback(size: int) -> Image.Image:
    fallback = Image.new("RGB", (size, size), (112, 112, 112))
    draw_fallback = ImageDraw.Draw(fallback)
    draw_fallback.rectangle([(0, 0), (size - 1, size - 1)], outline=(170, 170, 170), width=2)
    marker_radius = max(8, size // 10)
    center_x = size // 2
    marker_top = size // 3
    draw_fallback.ellipse(
        [
            (center_x - marker_radius, marker_top - marker_radius),
            (center_x + marker_radius, marker_top + marker_radius),
        ],
        fill=(220, 53, 69),
    )
    draw_fallback.polygon(
        [
            (center_x, marker_top + marker_radius + 8),
            (center_x - marker_radius // 2, marker_top + marker_radius - 2),
            (center_x + marker_radius // 2, marker_top + marker_radius - 2),
        ],
        fill=(220, 53, 69),
    )
    label_font = _load_font(14)
    label = "MAP"
    left, top, right, bottom = draw_fallback.textbbox((0, 0), label, font=label_font)
    draw_fallback.text(
        ((size - (right - left)) // 2, size - (bottom - top) - 10),
        label,
        font=label_font,
        fill=(245, 245, 245),
    )
    return fallback


def stamp_image_with_gps(
    image_path: Path,
    latitude: Optional[float],
    longitude: Optional[float],
    clock_time: datetime,
    address: Optional[str] = None,
) -> Path:
    image = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    img_width, img_height = image.size

    # Convert incoming UTC/naive timestamps to local wall time for human-readable image stamps.
    if clock_time.tzinfo is None:
        local_clock_time = clock_time.replace(tzinfo=timezone.utc).astimezone()
    else:
        local_clock_time = clock_time.astimezone()

    timestamp_text = local_clock_time.strftime("%d/%m/%Y %H:%M:%S")

    gps_available = _is_valid_coordinate_pair(latitude, longitude)
    if address and address.strip():
        resolved_address = address.strip()
    elif gps_available:
        resolved_address = reverse_geocode_address(latitude, longitude)
        if not resolved_address:
            resolved_address = f"{latitude:.6f}, {longitude:.6f}"
    else:
        resolved_address = "Location unavailable"

    if img_width >= 200:
        font_size = max(10, min(int(img_width * 0.028), 14))
        padding = 7
        max_box_width = int(img_width * 0.78)
        if max_box_width < 180:
            max_box_width = img_width - 24

        def _build_text_lines(current_font_size: int) -> list[str]:
            location_line = (
                f"Location: {latitude:.4f}° , {longitude:.4f}°"
                if gps_available
                else "Location: unavailable"
            )
            approx_wrap_width = int((max_box_width - (padding * 2)) / max(current_font_size * 0.62, 1))
            address_lines_local = textwrap.wrap(
                f"Address: {resolved_address}",
                width=max(22, min(35, approx_wrap_width)),
                break_long_words=False,
                break_on_hyphens=False,
            ) or [f"Address: {resolved_address}"]
            if len(address_lines_local) > 2:
                address_lines_local = [address_lines_local[0], f"{address_lines_local[1].rstrip()} ..."]
            return [f"Date & Time: {timestamp_text}", location_line, *address_lines_local]

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
        except Exception:
            font = _load_font(font_size)
        text_lines = _build_text_lines(font_size)
        line_spacing = max(3, font_size // 4)
        top_line_offset = line_spacing

        line_heights = []
        max_width = 0
        for line in text_lines:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            line_width = right - left
            line_height = bottom - top
            max_width = max(max_width, line_width)
            line_heights.append(line_height)

        total_text_height = top_line_offset + sum(line_heights) + (len(text_lines) - 1) * line_spacing
        box_width = max_width + (padding * 2)
        box_height = total_text_height + (padding * 2)

        while box_width > max_box_width and font_size > 10:
            font_size -= 1
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
            except Exception:
                font = _load_font(font_size)
            text_lines = _build_text_lines(font_size)
            line_spacing = max(3, font_size // 4)
            top_line_offset = line_spacing
            line_heights = []
            max_width = 0
            for line in text_lines:
                left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
                line_width = right - left
                line_height = bottom - top
                max_width = max(max_width, line_width)
                line_heights.append(line_height)
            total_text_height = top_line_offset + sum(line_heights) + (len(text_lines) - 1) * line_spacing
            box_width = max_width + (padding * 2)
            box_height = total_text_height + (padding * 2)

        x_start = 10
        y_start = img_height - box_height - 4
        if y_start < 0:
            y_start = 0

        try:
            draw.rounded_rectangle(
                [(x_start, y_start), (x_start + box_width, y_start + box_height)],
                radius=12,
                fill=(0, 0, 0, 125),
            )
        except AttributeError:
            draw.rectangle(
                [(x_start, y_start), (x_start + box_width, y_start + box_height)],
                fill=(0, 0, 0, 125),
            )

        text_x = x_start + padding
        text_y = y_start + padding + top_line_offset
        for index, line in enumerate(text_lines):
            draw.text(
                (text_x, text_y),
                line,
                font=font,
                fill=(255, 255, 255, 255),
            )
            text_y += line_heights[index] + line_spacing

    # Save stamped image to the same directory
    uploads_root = Path(__file__).resolve().parents[2] / "uploads"
    if uploads_root in image_path.resolve().parents:
        stamped_path = image_path.with_name(f"stamped_{image_path.stem}.jpg")
    else:
        fallback_dir = uploads_root / "staff" / "attendance"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        stamped_path = fallback_dir / f"stamped_{image_path.stem}.jpg"
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
