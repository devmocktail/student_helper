"""Hold the resume text the user pastes in, for the whole session.

The text is pasted directly in the app (no file reading), then injected
(condensed) into prompts so the tutor and the mock-interviewer know the
student's background, skills, and level.
"""


def condense(text, limit=6000):
    """Collapse whitespace and cap length so prompts stay small and cheap."""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit] + " ...(truncated)"
