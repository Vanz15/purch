SUSPICIOUS_PATTERNS = [
    "ignore previous", "ignore prior", "ignore all instructions",
    "disregard the", "you are now", "new instructions:",
    "system prompt", "act as",
]


def looks_like_injection(message: str) -> bool:
    lower = message.lower()
    return any(p in lower for p in SUSPICIOUS_PATTERNS)

def looks_like_multi_request(message: str) -> bool:
    lower = message.lower()
    return (" and " in lower or ";" in lower) and len(message.split()) > 8