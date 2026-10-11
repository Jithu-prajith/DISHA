"""
DISHA - Gemini Client
Single abstraction point for calling Gemini. Everything else in the app
talks to `ask()` and never touches the API directly — this is what makes
it easy to swap models, add tools, or go local later without rewriting
the UI or memory code.
"""

import socket
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
    return _model


def is_online(timeout: float = 2.0) -> bool:
    """Quick, cheap connectivity check before attempting an API call."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            ("8.8.8.8", 53)
        )
        return True
    except OSError:
        return False


def ask(prompt: str, context: str = "") -> str:
    """
    Send a prompt to Gemini and return DISHA's reply as plain text.
    Fails gracefully with a clear message if offline or the API errors out.
    """
    if not GEMINI_API_KEY:
        return "I don't have an API key set up yet — add one to your .env file."

    if not is_online():
        return "I'm offline right now, so I can't think that through. Reconnect and ask me again."

    try:
        model = _get_model()
        full_prompt = f"{context}\n\nUser: {prompt}" if context else prompt
        response = model.generate_content(full_prompt)
        return response.text.strip() if response.text else "I didn't get a response back — try rephrasing?"
    except Exception as e:
        return f"Something went wrong reaching Gemini: {e}"
