"""
DISHA - Memory
Deliberately minimal for v1: just a rolling log of recent exchanges so DISHA
can reference "what we talked about earlier" without a full vector-memory
system. This is state, not intelligence — kept boring on purpose.
"""

import json
from datetime import datetime
from config import MEMORY_FILE, MEMORY_MAX_ENTRIES


def log_exchange(user_input: str, disha_response: str) -> None:
    """Append one exchange to the local memory log."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user": user_input,
        "disha": disha_response,
    }
    try:
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        _trim_log()
    except OSError:
        # Memory logging should never crash the assistant
        pass


def _trim_log() -> None:
    """Keep only the most recent MEMORY_MAX_ENTRIES lines."""
    if not MEMORY_FILE.exists():
        return
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
    if len(lines) > MEMORY_MAX_ENTRIES:
        trimmed = lines[-MEMORY_MAX_ENTRIES:]
        MEMORY_FILE.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


def get_recent_context(n: int = 5) -> str:
    """Return the last n exchanges formatted as plain text context for Gemini."""
    if not MEMORY_FILE.exists():
        return ""
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()[-n:]
    if not lines:
        return ""

    formatted = []
    for line in lines:
        try:
            entry = json.loads(line)
            formatted.append(f"User: {entry['user']}\nDISHA: {entry['disha']}")
        except (json.JSONDecodeError, KeyError):
            continue

    if not formatted:
        return ""
    return "Recent conversation for context:\n" + "\n\n".join(formatted)
