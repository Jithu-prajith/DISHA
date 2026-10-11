# DISHA — Personal Desktop Companion (v1)

A lightweight, event-driven desktop assistant. Sits quietly in your system
tray, wakes on a hotkey, and answers using the Gemini API. No local model,
no background polling — idles at near-zero CPU/RAM until you call on it.

## What v1 does

- Greets you once when your laptop starts up — both a popup and spoken
  aloud, fully offline.
- Lives as a tray icon — click it, or press **Ctrl+Alt+D**, to type a
  question. Press **Ctrl+Alt+V** to talk to her instead (offline speech
  recognition, no internet needed).
- Understands local commands like "open vscode" or "open chrome" entirely
  offline — these never touch Gemini or the internet, so they work even
  with no connection and respond instantly.
- Anything that isn't a recognized local command falls through to Gemini
  for a real answer (this part does need internet).
- Speaks her responses aloud using your Windows' built-in offline voice
  engine — no internet needed for this either.
- Keeps a simple rolling log of your last ~20 exchanges so it has light
  context ("what did I ask earlier") — not full memory, just recent history.
- Fails gracefully if you're offline instead of freezing or crashing.
- Auto-launches silently every time you log into Windows — you never run
  `python main.py` manually after the initial setup.

## What it deliberately does NOT do yet

No local reasoning model (Gemini handles that), no screen understanding.
Voice and offline app-launching are in — reasoning and screen awareness
are the next layers to add later.

## Setup (Windows 11)

1. **Install Python 3.10+** if you don't have it: https://python.org

2. **Open a terminal in this folder** and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Get a Gemini API key:**
   Go to https://aistudio.google.com/apikey, create a key.

5. **Download the offline speech recognition model (Vosk):**
   - Go to https://alphacephei.com/vosk/models
   - Download **`vosk-model-small-en-us-0.15`** (~40MB — the small model is
     the right pick for your hardware; the larger ones are more accurate
     but noticeably heavier on CPU).
   - Unzip it.
   - Rename the unzipped folder to `model` and place it directly inside
     this `disha` folder, so you end up with `disha\model\` containing
     files like `am`, `conf`, `graph`, etc.

6. **Set up your `.env` file:**
   Copy `.env.example` to `.env` and paste your real API key in:
   ```
   copy .env.example .env
   ```
   Then edit `.env` and replace `your_api_key_here` with your actual key.

7. **Run it manually first, to test:**
   ```
   python main.py
   ```
   You should hear and see a greeting, then a tray icon appear. Press
   `Ctrl+Alt+D` to type a question, or `Ctrl+Alt+V` to speak one — try
   saying "open notepad" to test the offline command routing.

8. **Optional — run silently (no console window):**
   Once it works, use `pythonw.exe` instead of `python.exe` so no terminal
   window stays open:
   ```
   venv\Scripts\pythonw.exe main.py
   ```

## Auto-start on login (optional)

Run `setup_startup.bat` once. It registers a Windows Task Scheduler entry
that launches DISHA silently every time you log in — no console window,
no manual start needed. To undo it later:
```
schtasks /Delete /TN "DISHA_Assistant" /F
```

## Internet requirement

DISHA needs an internet connection to actually think — the reasoning
happens via the Gemini API, not locally. If you're offline, she'll tell
you clearly rather than hanging or crashing. Everything else (tray icon,
hotkey, popup UI) still works offline.

## Customizing DISHA's personality

Edit `SYSTEM_PROMPT` in `config.py` — that's her entire personality
definition in one place. Change tone, verbosity, whatever you want.

## Project structure

```
disha/
├── main.py            # entry point: tray icon, hotkeys, popup UI
├── gemini_client.py    # single abstraction for all Gemini API calls
├── voice.py             # offline STT (Vosk) + offline TTS (pyttsx3)
├── app_launcher.py      # offline local command routing (open/close apps)
├── memory.py           # simple rolling log of recent exchanges
├── config.py             # settings, personality prompt, app command map
├── requirements.txt
├── .env.example
├── setup_startup.bat     # registers permanent auto-start on login
├── model/                # Vosk offline speech model (you download this)
└── assets/
    └── icon.png          # optional — custom tray icon (falls back to a generated one)
```

## Customizing local commands

Edit `APP_COMMANDS` in `config.py` to add apps you actually use — say
"open spotify" or "open figma" and add the matching entry. This routing
is checked before Gemini, so it's instant and works fully offline.

## Why it's built this way

- **Single Gemini abstraction (`gemini_client.ask()`)** — every other part
  of the app calls this one function. When you later add local models,
  tool-calling, or MCP servers, you swap what's inside this function
  without touching the UI or memory code.
- **No polling loops** — the app is 100% event-driven (hotkey press, tray
  click). This is what keeps it from ever disturbing you or eating CPU
  while idle.
- **Memory kept boring on purpose** — a flat rolling log, not a vector
  database. Upgrade this later only once you actually have enough usage
  history that it matters.

## Next steps (once you're ready to expand)

- Swap the flat memory log for something structured once you're storing
  meaningful facts, not just chat history.
- Add a "morning context" tool that reads your recent git log to greet
  you with what you were working on, not just a generic hello.
- Add voice (STT/TTS) once the text flow feels solid and low-latency.
- Once your RAM upgrade lands, consider a small local model for narrow
  tasks (e.g. quick classification) to reduce reliance on the API for
  trivial things.
>>>>>>> c5860dc (Initial commit: Disha voice assistant project)
