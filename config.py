"""
DISHA - Configuration
Loads settings from a local .env file so the API key never sits in code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file sitting next to this script
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Hotkey used to summon DISHA's text input box
HOTKEY = os.getenv("DISHA_HOTKEY", "<ctrl>+<alt>+d")

# Hotkey used to trigger offline voice listening
VOICE_HOTKEY = os.getenv("DISHA_VOICE_HOTKEY", "<ctrl>+<alt>+v")

# --- Offline voice (STT + TTS) ---
# Download a small Vosk model (~50MB) from https://alphacephei.com/vosk/models
# e.g. "vosk-model-small-en-us-0.15", unzip it, and point this at the folder.
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", str(BASE_DIR / "model"))
TTS_ENABLED = os.getenv("DISHA_TTS_ENABLED", "true").lower() == "true"
TTS_RATE = int(os.getenv("DISHA_TTS_RATE", "175"))  # words per minute
TTS_VOICE_GENDER = os.getenv("DISHA_TTS_VOICE", "female")  # "female" or "male"
SILENCE_STOP_SECONDS = 1.4  # how long you can pause before DISHA stops listening

# --- Local app launcher ---
# Maps spoken/typed trigger words to the command DISHA runs. All of this is
# 100% local and offline — it never touches Gemini or the internet.
# Edit paths to match apps actually installed on your machine.
APP_COMMANDS = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "notepad": "notepad",
    "calculator": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "terminal": "wt",
    "command prompt": "cmd",
}

# How DISHA should behave/sound. Edit this freely — this is her personality.
SYSTEM_PROMPT = """You are DISHA, a personal desktop companion for a developer.
Keep replies short, warm, and useful — you sit quietly in the background and
only speak when asked. You are not a generic assistant; you are this user's
own companion. Avoid corporate or overly formal tone. Be direct, a little
warm, and never waste the user's time. If a question is ambiguous, make a
reasonable assumption and answer rather than asking for clarification, unless
truly necessary."""

# Local memory log (simple recent-history file, not a full memory system yet)
MEMORY_FILE = BASE_DIR / "memory_log.jsonl"
MEMORY_MAX_ENTRIES = 20  # how many recent exchanges to keep for context

# App metadata
APP_NAME = "DISHA"
ICON_PATH = BASE_DIR / "assets" / "icon.png"