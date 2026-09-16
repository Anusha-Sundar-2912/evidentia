import re
from dataclasses import dataclass, field


PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions?\b",
    r"\bignore\s+(all\s+)?prior\s+instructions?\b",
    r"\bdisregard\s+(all\s+)?previous\s+instructions?\b",
    r"\bforget\s+(all\s+)?previous\s+instructions?\b",
    r"\boverride\s+(the\s+)?system\s+(prompt|instructions?)\b",
    r"\breveal\s+(the\s+)?system\s+prompt\b",
    r"\bshow\s+(me\s+)?(your\s+)?system\s+prompt\b",
    r"\bprint\s+(the\s+)?system\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\bsystem\s+message\b.*\breveal\b",
    r"\bact\s+as\s+if\s+you\s+have\s+no\s+restrictions\b",
    r"\byou\s+are\s+now\s+in\s+developer\s+mode\b",
    r"\bbypass\s+(your\s+)?(rules|restrictions|guardrails)\b",
    r"\bdisable\s+(your\s+)?(safety|guardrails|restrictions)\b",
]


PII_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "phone": re.compile(
        r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
    ),
    "aadhaar": re.compile(
        r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"
    ),
    "pan": re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        re.IGNORECASE,
    ),
    "ipv4": re.compile(
        r"\b"
        r"(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
        r"\b"
    ),
}


PII_REPLACEMENTS = {
    "email": "[REDACTED_EMAIL]",
    "phone": "[REDACTED_PHONE]",
    "aadhaar": "[REDACTED_AADHAAR]",
    "pan": "[REDACTED_PAN]",
    "ipv4": "[REDACTED_IP]",
}


@dataclass
class GuardrailResult:
    allowed: bool
    original_text: str
    sanitized_text: str
    prompt_injection_detected: bool = False
    pii_detected: bool = False
    pii_types: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(
        default_factory=list
    )


def detect_prompt_injection(
    text: str,
) -> tuple[bool, list[str]]:
    detected_patterns = []

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            detected_patterns.append(
                pattern
            )

    return (
        bool(detected_patterns),
        detected_patterns,
    )


def detect_pii(
    text: str,
) -> list[str]:
    detected_types = []

    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            detected_types.append(
                pii_type
            )

    return detected_types


def redact_pii(
    text: str,
) -> tuple[str, list[str]]:
    sanitized_text = text
    detected_types = []

    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(
            sanitized_text
        ):
            detected_types.append(
                pii_type
            )

            sanitized_text = pattern.sub(
                PII_REPLACEMENTS[pii_type],
                sanitized_text,
            )

    return (
        sanitized_text,
        detected_types,
    )


def evaluate_input(
    text: str,
    redact_sensitive_data: bool = True,
) -> GuardrailResult:
    original_text = text

    injection_detected, _ = (
        detect_prompt_injection(
            text
        )
    )

    reasons = []

    if injection_detected:
        reasons.append(
            "prompt_injection_detected"
        )

    if redact_sensitive_data:
        sanitized_text, pii_types = (
            redact_pii(
                text
            )
        )
    else:
        sanitized_text = text
        pii_types = detect_pii(
            text
        )

    pii_detected = bool(
        pii_types
    )

    if pii_detected:
        reasons.append(
            "pii_detected"
        )

    return GuardrailResult(
        allowed=not injection_detected,
        original_text=original_text,
        sanitized_text=sanitized_text,
        prompt_injection_detected=(
            injection_detected
        ),
        pii_detected=pii_detected,
        pii_types=pii_types,
        reasons=reasons,
    )


def evaluate_output(
    text: str,
    redact_sensitive_data: bool = True,
) -> dict:
    """
    Inspect generated output before it leaves Evidentia.

    The original generated answer may be used internally
    for validation, but only sanitized_text should be
    returned to the user or stored in conversation memory.
    """

    if redact_sensitive_data:
        sanitized_text, pii_types = (
            redact_pii(
                text
            )
        )
    else:
        sanitized_text = text
        pii_types = detect_pii(
            text
        )

    pii_detected = bool(
        pii_types
    )

    return {
        "safe": not pii_detected,
        "pii_detected": pii_detected,
        "pii_types": pii_types,
        "pii_redacted": (
            sanitized_text != text
        ),
        "sanitized_text": sanitized_text,
    }