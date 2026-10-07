"""Thin wrapper around google-genai with streaming support.

`stream(...)` yields text chunks so the UI can render answers as they arrive.
`complete(...)` returns the full text (used for flashcard JSON generation).
"""

from app import config

_TYPES = None


def _lazy_imports():
    global _TYPES
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc
    _TYPES = types
    return genai, types


def _client(key=None):
    genai, _ = _lazy_imports()
    key = (key or config.load_key()).strip()
    if not key:
        raise RuntimeError(
            "No Gemini API key found. Add it in Settings, paste it into "
            "api_key.txt, or set the GEMINI_API_KEY environment variable."
        )
    return genai.Client(api_key=key)


def build_parts(prompt, image_png=None, resume_text=None, extra=None):
    """Assemble the `contents` list for a request."""
    _, types = _lazy_imports()
    parts = []
    if resume_text:
        parts.append(
            "CANDIDATE / STUDENT RESUME (context about their background and level):\n"
            + resume_text
        )
    parts.append(prompt)
    if extra:
        parts.append(extra)
    if image_png is not None:
        parts.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
    return parts


def stream(model, parts, key=None):
    """Yield text chunks from a streaming generation."""
    client = _client(key)
    response = client.models.generate_content_stream(
        model=model or config.DEFAULT_MODEL,
        contents=parts,
    )
    for chunk in response:
        text = getattr(chunk, "text", None)
        if text:
            yield text


def complete(model, parts, key=None):
    """Return the full response text in one shot."""
    client = _client(key)
    response = client.models.generate_content(
        model=model or config.DEFAULT_MODEL,
        contents=parts,
    )
    return (getattr(response, "text", "") or "").strip()
