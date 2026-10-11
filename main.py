"""
DISHA - Desktop Companion (v2)
Features:
- Floating Desktop Logo Widget (draggable anywhere on screen)
- Interactive Overlay Card (stays open after replying)
- Real-time Speech Transcription (shows live text as you speak)
- Voice Dismissal: Say or type "go", "exit", "bye", "close" to dismiss
- Dual Input Modes: Hotkey Ctrl+Alt+V (voice) / Ctrl+Alt+D (text) / Tray / Floating Widget click
"""

import socket
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

from config import APP_NAME, HOTKEY, VOICE_HOTKEY, ICON_PATH
import gemini_client
import memory
import app_launcher
import voice

# ---------------------------------------------------------------------------
# Single-instance guard
# ---------------------------------------------------------------------------
_LOCK_PORT = 54321
_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def acquire_single_instance_lock():
    try:
        _lock_socket.bind(("127.0.0.1", _LOCK_PORT))
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Exit Triggers ("go", "bye", "exit", "close", etc.)
# ---------------------------------------------------------------------------
EXIT_WORDS = {"go", "go away", "bye", "goodbye", "exit", "close", "dismiss", "hide", "stop", "shut up"}


def is_exit_command(text: str) -> bool:
    cleaned = text.strip().lower().rstrip(".!")
    return cleaned in EXIT_WORDS


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_request(user_input: str) -> str:
    local_response = app_launcher.try_local_command(user_input)
    if local_response is not None:
        memory.log_exchange(user_input, local_response)
        return local_response

    context = memory.get_recent_context()
    answer = gemini_client.ask(user_input, context)
    memory.log_exchange(user_input, answer)
    return answer


# ---------------------------------------------------------------------------
# Screen Helper
# ---------------------------------------------------------------------------

def center_window(win, width: int, height: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 3)
    win.geometry(f"{width}x{height}+{x}+{y}")


# ---------------------------------------------------------------------------
# DISHA Interactive Overlay Window
# ---------------------------------------------------------------------------
_assistant_window = None


class DishaAssistantWindow:
    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title("DISHA Companion")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1e1e2e")
        center_window(self.win, 500, 320)

        # Allow dragging the window by header
        self._drag_data = {"x": 0, "y": 0}

        self._build_ui()

    def _build_ui(self):
        # Header / Title Bar
        header = tk.Frame(self.win, bg="#181825", height=38)
        header.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header,
            text="✨ DISHA Desktop Companion",
            bg="#181825",
            fg="#a6e3a1",
            font=("Segoe UI", 11, "bold"),
        )
        title_lbl.pack(side="left", padx=14, pady=6)

        close_btn = tk.Label(
            header,
            text=" ✕ ",
            bg="#181825",
            fg="#f38ba8",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
        )
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Button-1>", lambda e: self.close())

        header.bind("<Button-1>", self._start_drag)
        header.bind("<B1-Motion>", self._do_drag)
        title_lbl.bind("<Button-1>", self._start_drag)
        title_lbl.bind("<B1-Motion>", self._do_drag)

        # Main Text Conversation Area
        content = tk.Frame(self.win, bg="#1e1e2e")
        content.pack(fill="both", expand=True, padx=16, pady=10)

        self.status_var = tk.StringVar(value="Ready. Press 🎤 Speak, type below, or say 'go' to exit.")
        self.display_label = tk.Label(
            content,
            textvariable=self.status_var,
            bg="#313244",
            fg="#cdd6f4",
            font=("Segoe UI", 11),
            wraplength=450,
            justify="left",
            anchor="nw",
            bd=0,
            padx=12,
            pady=12,
        )
        self.display_label.pack(fill="both", expand=True)

        # Input Area (Text entry + Speak button)
        input_frame = tk.Frame(self.win, bg="#1e1e2e")
        input_frame.pack(fill="x", side="bottom", padx=16, pady=(0, 14))

        self.entry = tk.Entry(
            input_frame,
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            font=("Segoe UI", 11),
            bd=1,
            relief="solid",
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.submit_text())

        send_btn = tk.Button(
            input_frame,
            text="Send",
            bg="#89b4fa",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.submit_text,
        )
        send_btn.pack(side="left", padx=(0, 6))

        speak_btn = tk.Button(
            input_frame,
            text="🎤 Listen",
            bg="#a6e3a1",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.start_listening,
        )
        speak_btn.pack(side="left")

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.win.winfo_x() + deltax
        y = self.win.winfo_y() + deltay
        self.win.geometry(f"+{x}+{y}")

    def focus_text_input(self):
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.entry.focus_set()

    def start_listening(self):
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.status_var.set("🎤 Listening... Speak now.")

        def on_partial(text):
            self.root.after(0, lambda: self.status_var.set(f"🎤 Hearing: {text}"))

        def worker():
            try:
                heard = voice.listen(on_partial=on_partial)
            except RuntimeError as e:
                self.root.after(0, lambda: self.status_var.set(f"Microphone error: {e}"))
                return

            if not heard:
                self.root.after(0, lambda: self.status_var.set("Didn't catch anything. Click 🎤 Listen or type below."))
                return

            if is_exit_command(heard):
                self.root.after(0, lambda: self.status_var.set("Goodbye!"))
                voice.speak("Goodbye!", wait=True)
                self.root.after(500, self.close)
                return

            self.root.after(0, lambda: self.status_var.set(f"You: {heard}\n\nThinking..."))
            answer = route_request(heard)
            self.root.after(0, lambda: self.status_var.set(f"You: {heard}\n\nDISHA: {answer}"))
            voice.speak(answer, wait=False)

        threading.Thread(target=worker, daemon=True).start()

    def submit_text(self):
        query = self.entry.get().strip()
        if not query:
            return
        self.entry.delete(0, tk.END)

        if is_exit_command(query):
            self.status_var.set("Goodbye!")
            voice.speak("Goodbye!", wait=True)
            self.close()
            return

        self.status_var.set(f"You: {query}\n\nThinking...")

        def worker():
            answer = route_request(query)
            self.root.after(0, lambda: self.status_var.set(f"You: {query}\n\nDISHA: {answer}"))
            voice.speak(answer, wait=False)

        threading.Thread(target=worker, daemon=True).start()

    def close(self):
        global _assistant_window
        _assistant_window = None
        try:
            self.win.destroy()
        except Exception:
            pass


def open_or_focus_assistant(root, mode: str = "voice"):
    global _assistant_window
    if _assistant_window is None or not tk.Toplevel.winfo_exists(_assistant_window.win):
        _assistant_window = DishaAssistantWindow(root)

    if mode == "voice":
        _assistant_window.start_listening()
    else:
        _assistant_window.focus_text_input()


# ---------------------------------------------------------------------------
# Floating Desktop Logo Widget
# ---------------------------------------------------------------------------

class DesktopLogoWidget:
    """
    A sleek, draggable floating desktop avatar logo widget.
    Sits gracefully on your desktop. Click to open DISHA!
    """

    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#11111b")

        # Position near top-right of primary screen
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        x = max(20, sw - 120)
        y = 100
        self.win.geometry(f"64x64+{x}+{y}")

        # Make background transparent so only the circular avatar floats
        try:
            self.win.wm_attributes("-transparentcolor", "#11111b")
        except Exception:
            pass

        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)

        self._drag_data = {"x": 0, "y": 0}

        # Create glowing rounded avatar canvas
        canvas = tk.Canvas(self.win, width=64, height=64, bg="#11111b", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Draw dark circle with green accent border
        canvas.create_oval(4, 4, 60, 60, fill="#1e1e2e", outline="#a6e3a1", width=3)
        canvas.create_text(32, 31, text="D", fill="#a6e3a1", font=("Segoe UI", 22, "bold"))

        canvas.bind("<Button-1>", self._on_click)
        canvas.bind("<B1-Motion>", self._on_drag)

    def _on_click(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        # Open DISHA window on click
        open_or_focus_assistant(self.root, mode="voice")

    def _on_drag(self, event):
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.win.winfo_x() + deltax
        y = self.win.winfo_y() + deltay
        self.win.geometry(f"+{x}+{y}")


# ---------------------------------------------------------------------------
# System Tray Icon
# ---------------------------------------------------------------------------

def make_icon_image():
    if ICON_PATH.exists():
        return Image.open(ICON_PATH)
    img = Image.new("RGB", (64, 64), "#1e1e2e")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill="#a6e3a1")
    draw.text((24, 22), "D", fill="#1e1e2e")
    return img


def build_tray_icon(root):
    def on_voice(icon, item):
        root.after(0, lambda: open_or_focus_assistant(root, mode="voice"))

    def on_text(icon, item):
        root.after(0, lambda: open_or_focus_assistant(root, mode="text"))

    def on_quit(icon, item):
        icon.stop()
        root.after(0, root.quit)

    menu = pystray.Menu(
        pystray.MenuItem("Speak to DISHA (Ctrl+Alt+V)", on_voice, default=True),
        pystray.MenuItem("Type to DISHA (Ctrl+Alt+D)", on_text),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon(APP_NAME, make_icon_image(), APP_NAME, menu)
    return icon


# ---------------------------------------------------------------------------
# Global Hotkey Listener
# ---------------------------------------------------------------------------

def start_hotkey_listener(root):
    def on_voice():
        root.after(0, lambda: open_or_focus_assistant(root, mode="voice"))

    def on_text():
        root.after(0, lambda: open_or_focus_assistant(root, mode="text"))

    try:
        hotkey = keyboard.GlobalHotKeys({
            VOICE_HOTKEY: on_voice,
            HOTKEY: on_text,
        })
        hotkey.start()
        return hotkey
    except Exception as e:
        print(f"Hotkey registration warning: {e}")
        return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not acquire_single_instance_lock():
        sys.exit(0)

    root = tk.Tk()
    root.withdraw()

    # Launch Desktop Floating Logo Widget
    DesktopLogoWidget(root)

    # Launch System Tray Icon
    icon = build_tray_icon(root)
    threading.Thread(target=icon.run, daemon=True).start()

    # Launch Hotkeys
    start_hotkey_listener(root)

    # Startup Voice Greeting
    threading.Thread(
        target=lambda: voice.speak(f"Hey, {APP_NAME} here. Click my icon or press Control Alt V whenever you need me."),
        daemon=True,
    ).start()

    root.mainloop()


if __name__ == "__main__":
    main()