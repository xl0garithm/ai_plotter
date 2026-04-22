"""Central definition for style presets."""

from __future__ import annotations

from typing import Dict

# Shared preset instructions—mirror the Gemini base prompt to keep outputs plotter-safe.
BASE_PROMPT = (
    "Use only bold #000 ink lines on a pure white background so the drawing can be plotted with one pen. "
    "Never introduce shading, gradients, halftones, gray pixels, hatching, or fills; if tone would appear, rework the idea as solid contour lines. "
    "Keep everything as a single confident continuous outline with exaggerated caricature proportions, and express styles through props or silhouette changes instead of color. "
    "If using text anywhere, render only oversized block lettering with extremely bold, thick contour lines so the SVG converter reliably captures it."
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
    "roast_me": {
        "label": "Roast me",
        "description": "Hyper-caricature that mercilessly exaggerates whatever stands out about the subject.",
        "prompt": (
            f"{BASE_PROMPT}"
            "Do a brutal-but-fun roast caricature: spot the person’s most distinctive traits—ears, nose, jawline, hair swoop, "
            "glasses, posture—and blow them way out of proportion while keeping the likeness readable. "
            "Lean into asymmetry, highlight laugh lines or under-eye bags, and sprinkle in roast props (tiny crown, speech bubble, "
            "award ribbon) only if they reinforce the joke. Keep everything a single confident outline."
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

