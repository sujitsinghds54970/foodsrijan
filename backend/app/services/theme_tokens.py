import re
from copy import deepcopy
from typing import Any


TOKEN_CATEGORIES = {
    "color": ["palette", "semantic", "surface", "text", "border"],
    "typography": ["family", "size", "weight", "line_height", "letter_spacing"],
    "spacing": ["scale", "padding", "margin", "gap"],
    "radius": ["none", "sm", "md", "lg", "xl", "pill"],
    "shadow": ["elevation_1", "elevation_2", "elevation_3", "elevation_4"],
    "gradient": ["families"],
    "motion": ["duration", "easing"],
    "icon": ["size", "stroke"],
}

APPROVED_FONTS = {"Fraunces", "Manrope", "Inter", "system-ui", "Georgia", "sans-serif", "serif"}
COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([^()]+\)|hsla?\([^()]+\)|oklch\([^()]+\))$")
FORBIDDEN_RE = re.compile(r"[<>{};`]|url\s*\(", re.IGNORECASE)
REQUIRED_SEMANTIC = ("primary", "secondary", "accent", "success", "warning", "danger")


def default_tokens() -> dict[str, Any]:
    return {
        "color": {
            "palette": {"gold": "#D6A84F", "violet": "#8C78F5", "teal": "#2DD4BF"},
            "semantic": {"primary": "#8B5E17", "secondary": "#8C78F5", "accent": "#57C7F2", "success": "#56C58A", "warning": "#E8A24A", "danger": "#E87986"},
            "surface": {"default": "#090B14", "panel": "#25293D", "elevated": "#2B2F45"},
            "text": {"primary": "#FFF9EC", "secondary": "#D2CFD8", "tertiary": "#B7B5C1"},
            "border": {"default": "#4B4D5A", "focus": "#F3D58A"},
        },
        "typography": {"family": {"display": "Fraunces", "body": "Manrope"}, "size": {"base": "16px", "sm": "12px", "lg": "20px"}, "weight": {"regular": 400, "semibold": 600, "bold": 700}, "line_height": {"base": 1.5}, "letter_spacing": {"base": "0px"}},
        "spacing": {"scale": [0, 4, 8, 12, 16, 24, 32], "padding": {"sm": "8px", "md": "16px", "lg": "24px"}, "margin": {"sm": "8px", "md": "16px", "lg": "24px"}, "gap": {"sm": "8px", "md": "16px", "lg": "24px"}},
        "radius": {"none": "0px", "sm": "8px", "md": "12px", "lg": "20px", "xl": "28px", "pill": "999px"},
        "shadow": {"elevation_1": "0 2px 8px rgba(0,0,0,.18)", "elevation_2": "0 8px 20px rgba(0,0,0,.22)", "elevation_3": "0 18px 44px rgba(0,0,0,.28)", "elevation_4": "0 28px 80px rgba(0,0,0,.42)"},
        "gradient": {"families": {}},
        "motion": {"duration": {"fast": "120ms", "normal": "220ms", "slow": "400ms"}, "easing": {"standard": "ease", "emphasized": "ease-in-out"}},
        "icon": {"size": 24, "stroke": 1.5},
    }


def _walk(values: Any, path: str = ""):
    if isinstance(values, dict):
        for key, value in values.items():
            yield from _walk(value, f"{path}.{key}" if path else key)
    elif isinstance(values, list):
        for index, value in enumerate(values):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, values


def validate_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(tokens, dict):
        return {"valid": False, "errors": ["Tokens must be an object"]}
    for category in TOKEN_CATEGORIES:
        if category not in tokens:
            errors.append(f"Missing category: {category}")
    semantic = tokens.get("color", {}).get("semantic", {})
    for name in REQUIRED_SEMANTIC:
        if name not in semantic:
            errors.append(f"Missing required semantic token: color.semantic.{name}")
    for path, value in _walk(tokens):
        if not isinstance(value, str):
            continue
        if FORBIDDEN_RE.search(value):
            errors.append(f"Unsafe token value at {path}")
        if path.startswith(("color.", "gradient.")) and not value.startswith("{") and not COLOR_RE.match(value) and not any(part in path for part in ("family", "easing", "duration", "size", "weight", "line_height", "letter_spacing", "shadow")):
            errors.append(f"Invalid color value at {path}")
    families = tokens.get("typography", {}).get("family", {})
    for path, value in _walk(families, "typography.family"):
        if value not in APPROVED_FONTS:
            errors.append(f"Unapproved font family at {path}")
    return {"valid": not errors, "errors": errors}


def merge_tokens(*documents: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for document in documents:
        if not document:
            continue
        for key, value in document.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = merge_tokens(result[key], value)
            else:
                result[key] = deepcopy(value)
    return result
