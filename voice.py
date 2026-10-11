"""
DISHA - Offline Voice
Speech-to-text via Vosk (fully local model, no internet) and text-to-speech
via pyttsx3 (uses Windows' built-in SAPI5 engine, also fully local).
Neither of these ever touches the network.
"""

import json
import queue

import sounddevice as sd
import vosk
import pyttsx3

from config import VOSK_MODEL_PATH, TTS_ENABLED, TTS_RATE, TTS_VOICE_GENDER, SILENCE_STOP_SECONDS

import ctypes
import threading

import win32com.client

vosk.SetLogLevel(-1)  # quiet Vosk's default console spam

_stt_model = None
_tts_queue = queue.Queue()
_tts_thread = None


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------

def _tts_speak_direct_sapi(text: str) -> bool:
    """
    Direct Windows SAPI5 COM dispatch. Bypasses pyttsx3 driver loops and
    guarantees audio output on Windows 10/11 even after microphone input.
    """
    try:
        ctypes.windll.ole32.CoInitialize(None)
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            try:
                voices = speaker.GetVoices()
                for i in range(voices.Count):
                    v = voices.Item(i)
                    desc = (v.GetDescription() or "").lower()
                    if TTS_VOICE_GENDER == "female" and ("zira" in desc or "female" in desc):
                        speaker.Voice = v
                        break
                    elif TTS_VOICE_GENDER == "male" and ("david" in desc or "male" in desc):
                        speaker.Voice = v
                        break
            except Exception:
                pass
            speaker.Speak(text)
            del speaker
            return True
        finally:
            ctypes.windll.ole32.CoUninitialize()
    except Exception:
        return False


def _tts_worker():
    """
    Dedicated worker thread loop for TTS.
    Tries native Windows SAPI.SpVoice first, falling back to pyttsx3.
    """
    while True:
        item = _tts_queue.get()
        if item is None:
            _tts_queue.task_done()
            break
        text, done_event = item
        if TTS_ENABLED and text:
            success = _tts_speak_direct_sapi(text)
            if not success:
                try:
                    ctypes.windll.ole32.CoInitialize(None)
                    try:
                        engine = pyttsx3.init()
                        engine.setProperty("rate", TTS_RATE)
                        _select_voice(engine, TTS_VOICE_GENDER)
                        engine.say(text)
                        engine.runAndWait()
                        del engine
                    finally:
                        ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass
        if done_event:
            done_event.set()
        _tts_queue.task_done()


def _ensure_tts_thread():
    global _tts_thread
    if _tts_thread is None or not _tts_thread.is_alive():
        _tts_thread = threading.Thread(target=_tts_worker, daemon=True)
        _tts_thread.start()


def _select_voice(engine, preferred_gender: str) -> None:
    """
    Pick a matching installed voice (e.g. Windows' built-in "Zira" for
    female, "David" for male). Falls back to whatever's default if no
    match is found — never errors out.
    """
    try:
        voices = engine.getProperty("voices")
    except Exception:
        return

    for v in voices:
        name = (v.name or "").lower()
        v_id = (v.id or "").lower()
        if preferred_gender == "female" and ("zira" in name or "female" in name or "zira" in v_id):
            engine.setProperty("voice", v.id)
            return
        if preferred_gender == "male" and ("david" in name or "male" in name or "david" in v_id):
            engine.setProperty("voice", v.id)
            return


def speak(text: str, wait: bool = False) -> None:
    """
    Speak text aloud, fully offline. No-op if TTS is disabled in config.
    If wait is True, blocks the calling thread until speaking is complete.
    """
    if not TTS_ENABLED or not text:
        return
    _ensure_tts_thread()
    done_event = threading.Event() if wait else None
    _tts_queue.put((text, done_event))
    if wait and done_event:
        done_event.wait()



# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------

def _get_stt_model():
    global _stt_model
    if _stt_model is None:
        try:
            _stt_model = vosk.Model(VOSK_MODEL_PATH)
        except Exception as e:
            raise RuntimeError(
                f"Couldn't load the Vosk model at '{VOSK_MODEL_PATH}'. "
                f"Download a model from https://alphacephei.com/vosk/models, "
                f"unzip it, and set VOSK_MODEL_PATH to that folder. ({e})"
            )
    return _stt_model


def listen(sample_rate: int = 16000, max_seconds: float = 12.0, on_partial=None) -> str:
    """
    Listen on the default microphone until you pause for
    SILENCE_STOP_SECONDS, then return the transcribed text.
    Supports on_partial callback for live real-time speech transcription display.
    """
    model = _get_stt_model()
    recognizer = vosk.KaldiRecognizer(model, sample_rate)

    audio_queue: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        audio_queue.put(bytes(indata))

    silence_chunks_needed = int(SILENCE_STOP_SECONDS * sample_rate / 8000)
    silence_streak = 0
    heard_something = False
    transcript_parts = []

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            total_chunks = int(max_seconds * sample_rate / 8000)
            for _ in range(total_chunks):
                data = audio_queue.get()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        transcript_parts.append(text)
                        heard_something = True
                        silence_streak = 0
                        if on_partial:
                            on_partial(" ".join(transcript_parts))
                    else:
                        silence_streak += 1
                else:
                    partial = json.loads(recognizer.PartialResult())
                    p_text = partial.get("partial", "")
                    if p_text:
                        heard_something = True
                        silence_streak = 0
                        if on_partial:
                            current_text = " ".join(transcript_parts + [p_text]).strip()
                            on_partial(current_text)
                    else:
                        silence_streak += 1

                if heard_something and silence_streak >= silence_chunks_needed:
                    break
    except Exception as e:
        raise RuntimeError(f"Microphone error: {e}")

    final = json.loads(recognizer.FinalResult())
    if final.get("text"):
        transcript_parts.append(final["text"])

    return " ".join(transcript_parts).strip()