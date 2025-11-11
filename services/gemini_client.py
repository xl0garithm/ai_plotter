"""Client for interacting with the Gemini image generation API."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import requests


class GeminiClientError(RuntimeError):
    """Raised when Gemini API interaction fails."""


@dataclass
class GeminiClient:
    """REST client for Gemini image generation."""

    api_key: str
    model: str
    endpoint: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout: int = 60

    def generate_caricature(self, image_bytes: bytes, prompt: Optional[str] = None) -> bytes:
        """Generate a caricature image using the Gemini API."""
        if not self.api_key:
            raise GeminiClientError("Gemini API key is not configured.")

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        model_name = self.model.removeprefix("models/")
        url = f"{self.endpoint}/models/{model_name}:generateContent"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                            or "Create a high-contrast caricature of the provided portrait suitable for vector plotting."
                        },
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": encoded_image,
                            }
                        },
                    ],
                }
            ]
        }

        params = {"key": self.api_key}

        try:
            response = requests.post(url, json=payload, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            details = ""
            if exc.response is not None:
                try:
                    details = f" Response: {exc.response.text}"
                except Exception:  # noqa: BLE001
                    details = ""
            raise GeminiClientError(f"Gemini request failed: {exc}.{details}") from exc

        data = response.json()
        try:
            encoded_output = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiClientError("Gemini response missing expected image data.") from exc

        return base64.b64decode(encoded_output)

