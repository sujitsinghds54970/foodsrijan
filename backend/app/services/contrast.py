import re
from typing import Any


def _rgb(value: str) -> tuple[float, float, float] | None:
    if not value:
        return None
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) in (3, 4):
            raw = "".join(char * 2 for char in raw[:3])
        if len(raw) >= 6:
            return tuple(int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4))
    match = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", value)
    if match:
        return tuple(min(float(match.group(index)) / 255, 1) for index in (1, 2, 3))
    return None


def _luminance(value: str) -> float | None:
    rgb = _rgb(value)
    if rgb is None:
        return None
    channels = [((channel + 0.055) / 1.055) ** 2.4 if channel > 0.03928 else channel / 12.92 for channel in rgb]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def ratio(foreground: str, background: str) -> float | None:
    first, second = _luminance(foreground), _luminance(background)
    if first is None or second is None:
        return None
    lighter, darker = max(first, second), min(first, second)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def check_contrast(tokens: dict[str, Any]) -> dict[str, Any]:
    colors = tokens.get("color", {})
    text = colors.get("text", {})
    surface = colors.get("surface", {})
    semantic = colors.get("semantic", {})
    pairs = [
        ("text_primary_on_surface_default", text.get("primary"), surface.get("default"), 4.5),
        ("text_secondary_on_surface_default", text.get("secondary"), surface.get("default"), 4.5),
        ("text_primary_on_primary_action", text.get("primary"), semantic.get("primary"), 4.5),
        ("focus_indicator_on_surface_default", colors.get("border", {}).get("focus"), surface.get("default"), 3.0),
    ]
    failures = []
    results = []
    for name, foreground, background, minimum in pairs:
        actual = ratio(foreground, background) if foreground and background else None
        passed = actual is not None and actual >= minimum
        item = {"pair": name, "foreground": foreground, "background": background, "ratio": actual, "minimum": minimum, "passed": passed}
        results.append(item)
        if not passed:
            failures.append(item)
    return {"passed": not failures, "failures": failures, "results": results}
