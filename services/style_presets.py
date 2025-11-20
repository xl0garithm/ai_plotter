"""Central definition for style presets."""

from __future__ import annotations

from typing import Dict

BASE_PROMPT = (
    "Use thick, confident single-line outlines with clean contours and no shading so the art stays "
    "pen-plotter friendly. "
    "Push the drawing into a comedic caricature: exaggerate signature traits, lean into flaws, and keep it a single, "
    "continuous stroke. When a style calls out a theme, add obvious costume pieces, props, or body mods—not just line tweaks."
)

STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "nerdy": {
        "label": "Nerdy",
        "description": "Crisp outlines with confident energy—great for glasses and hoodie detail.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Turn the subject into an over-the-top nerd caricature: massive round glasses, a too-wide grin with braces, "
            "messy hair, and a hoodie packed with gadgets or a pocket protector spilling pens. Make the props obvious "
            "while keeping one flowing outline."
        ),
    },
    "goofy": {
        "label": "Goofy",
        "description": "Playful curves with exaggerated expressions and a carefree look.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Make them look hilariously goofy with an off-balance head tilt, bulging cheeks, extra-wide teeth, "
            "mismatched pupils, and silly accessories like party hats or squeaky toys—all captured in one playful stroke."
        ),
    },
    "funny": {
        "label": "Funny",
        "description": "Loose lines, expressive eyebrows, and a bigger grin for comedic charm.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Dial up the comedic embarrassment: oversized eyebrows arcing off the face, a bulbous nose, and a roaring laugh "
            "with wobbling shoulders or cartoon sweat drops to telegraph motion, all while staying in one continuous line."
        ),
    },
    "cyberpunk": {
        "label": "Cyberpunk",
        "description": "Angular strokes with subtle sci-fi visor highlights and high-tech flair.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Go full cyberpunk caricature with cyborg jaw plates, exposed wiring, a glowing HUD visor, mech shoulder pads, "
            "neon cables, or a chrome arm. Make the upgrades obvious body mods layered onto the subject while keeping the "
            "single-line simplicity."
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

