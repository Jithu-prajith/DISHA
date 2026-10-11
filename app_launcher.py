"""
DISHA - Local App Launcher
Fully offline command routing. Checked BEFORE Gemini is ever called, so
"open vscode" is instant and works with no internet connection at all.
Only unrecognized input falls through to the Gemini API.
"""

import subprocess
from typing import Optional

from config import APP_COMMANDS

OPEN_TRIGGERS = ("open ", "launch ", "start ")
CLOSE_TRIGGERS = ("close ", "quit ", "kill ")


def try_local_command(text: str) -> Optional[str]:
    """
    If `text` matches a known local command (open/close an app), execute it
    and return a confirmation string. Returns None if nothing matched, so
    the caller knows to fall back to Gemini.
    """
    lowered = text.strip().lower()

    for trigger in OPEN_TRIGGERS:
        if lowered.startswith(trigger):
            app_name = lowered[len(trigger):].strip()
            return _launch_app(app_name)

    for trigger in CLOSE_TRIGGERS:
        if lowered.startswith(trigger):
            app_name = lowered[len(trigger):].strip()
            return _close_app(app_name)

    return None


def _launch_app(app_name: str) -> Optional[str]:
    command = APP_COMMANDS.get(app_name)
    if not command:
        # Not a recognized app — let it fall through to Gemini instead of
        # failing silently, in case it's a genuine question containing "open".
        return None
    try:
        subprocess.Popen(command, shell=True)
        return f"Opening {app_name}."
    except OSError as e:
        return f"Couldn't open {app_name}: {e}"


def _close_app(app_name: str) -> Optional[str]:
    command = APP_COMMANDS.get(app_name)
    if not command:
        return None
    # taskkill matches on the executable name, not the alias — this is a
    # best-effort mapping and may need tuning per-app.
    exe_guess = command if command.endswith(".exe") else f"{command}.exe"
    try:
        subprocess.run(
            ["taskkill", "/IM", exe_guess, "/F"],
            shell=True,
            capture_output=True,
        )
        return f"Closed {app_name}."
    except OSError as e:
        return f"Couldn't close {app_name}: {e}"
