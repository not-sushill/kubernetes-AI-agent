"""Conservative timeout evidence matching shared by detection and correlation."""
import re

_FAILURE = re.compile(
    r"\btimed\s+out\b|\bdeadline\s+exceeded\b|\bETIMEDOUT\b|"
    r"\b(?:[A-Za-z]*Timeout(?:Error|Exception))\b|"
    r"\btimeout\s+(?:error|exception|expired|exceeded|occurred)\b|"
    r"\b(?:request|connection|connect|read|write|socket|upstream|gateway)\s+timeout\b",
    re.IGNORECASE,
)
_CONFIGURATION = re.compile(
    r"\b(?:initializing|configuration|configured|config|setting|set to)\b|"
    r"\btimeout\s*(?:[:=]\s*)?\d+\b",
    re.IGNORECASE,
)
_EXPLICIT_FAILURE = re.compile(
    r"\btimed\s+out\b|\bdeadline\s+exceeded\b|\bETIMEDOUT\b|"
    r"\b[A-Za-z]*Timeout(?:Error|Exception)\b",
    re.IGNORECASE,
)


def is_timeout_failure(line: str) -> bool:
    if not _FAILURE.search(line):
        return False
    return bool(_EXPLICIT_FAILURE.search(line) or not _CONFIGURATION.search(line))
