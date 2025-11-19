"""Client for interacting with the Gemini image generation API."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import requests


class GeminiClientError(RuntimeError):
    """Raised when Gemini API interaction fails."""


BASE_PROMPT = (
    "Create a simple, clean black-and-white caricature of the person in the provided photo. "
    "Render as a single continuous outline with minimal detail - focus on the most essential facial features only. "
    "Use thick, smooth black lines on a white background suitable for pen plotting. "
    "Avoid small details, shading, or fills. Keep it simple and continuous for clean G-code conversion. "
    "Return only the final outline image without any text, captions, or borders."
)


@dataclass
class GeminiClient:
    """REST client for Gemini image generation."""

    api_key: str
    model: str
    endpoint: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout: int = 60
    max_attempts: int = 2

    def generate_caricature(self, image_bytes: bytes, prompt: Optional[str] = None) -> bytes:
        """Generate a caricature image using the Gemini API."""
        if not self.api_key:
            raise GeminiClientError("Gemini API key is not configured.")

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        final_prompt = BASE_PROMPT
        if prompt:
            final_prompt = f"{BASE_PROMPT} Additional instructions: {prompt}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": final_prompt},
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

        last_error: Optional[GeminiClientError] = None

        for _ in range(max(1, self.max_attempts)):
            try:
                data = self._post_and_parse(payload)
                encoded_output = self._extract_inline_image(data)
                if encoded_output:
                    return base64.b64decode(encoded_output)
                last_error = GeminiClientError(
                    "Gemini response missing expected image data; retrying for outline image."
                )
            except GeminiClientError as exc:
                last_error = exc

        if last_error:
            raise last_error
        raise GeminiClientError("Gemini generation failed for an unknown reason.")

    def _post_and_parse(self, payload: dict) -> dict:
        """Send request to Gemini and return JSON data."""
        model_name = self.model.removeprefix("models/")
        url = f"{self.endpoint}/models/{model_name}:generateContent"
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

        return response.json()

    @staticmethod
    def _extract_inline_image(response_data: dict) -> Optional[str]:
        """Find the first inlineData entry containing base64 image data."""
        candidates = response_data.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                inline = part.get("inlineData")
                if inline:
                    data = inline.get("data")
                    if data:
                        return data
        return None

