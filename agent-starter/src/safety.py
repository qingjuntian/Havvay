import re


class UnsafePromptError(ValueError):
    """Raised when a prompt matches a clearly unsafe request pattern."""


class SafetyLayer:
    _DENYLIST = (
        r"\b(?:steal|hack|ransomware|keylogger)\b",
        r"\b(?:make|build|create)\s+(?:a\s+)?(?:bomb|weapon)\b",
        r"\b(?:bypass|disable)\s+(?:security|authentication|access controls?)\b",
    )

    def validate(self, prompt: str) -> str:
        normalized = prompt.strip()
        if not normalized:
            raise UnsafePromptError("Prompt must not be empty.")
        if len(normalized) > 8000:
            raise UnsafePromptError("Prompt is too long.")
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in self._DENYLIST):
            raise UnsafePromptError("Prompt is not allowed.")
        return normalized
