"""Central definition for style presets."""

from __future__ import annotations

from typing import Dict

BASE_PROMPT = (
    "Use thick, confident single-line outlines with clean contours and no shading so the art stays "
    "pen-plotter friendly. "
)

STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "nerdy": {
        "label": "Nerdy",
        "description": "Crisp outlines with confident energy—great for glasses and hoodie detail.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Add clever, nerdy energy with thick round glasses, a confident grin, and crisp hoodie detail while "
            "preserving the single continuous line style."
        ),
    },
    "goofy": {
        "label": "Goofy",
        "description": "Playful curves with exaggerated expressions and a carefree look.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Create a playful, goofy caricature with exaggerated expressions and round, bouncy lines while staying "
            "within a single continuous outline."
        ),
    },
    "funny": {
        "label": "Funny",
        "description": "Loose lines, expressive eyebrows, and a bigger grin for comedic charm.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Emphasize comedic charm with loose continuous lines, expressive eyebrows, and an oversized smile."
        ),
    },
    "cyberpunk": {
        "label": "Cyberpunk",
        "description": "Angular strokes with subtle sci-fi visor highlights and high-tech flair.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Blend the portrait with sleek cyberpunk elements—subtle visor highlights, angular lines, and high-tech "
            "accessories while keeping the minimal outline."
        ),
    },
}

DEFAULT_STYLE_KEY = "nerdy"


def get_style(style_key: str) -> Dict[str, str]:
    """Return the preset; fallback to default if missing."""
    return STYLE_PRESETS.get(style_key, STYLE_PRESETS[DEFAULT_STYLE_KEY])


def get_ui_style_map() -> Dict[str, Dict[str, str]]:
    """Return a sanitized version (no prompts) for frontend display."""
    return {
        key: {"label": value["label"], "description": value["description"]}
        for key, value in STYLE_PRESETS.items()
    }

