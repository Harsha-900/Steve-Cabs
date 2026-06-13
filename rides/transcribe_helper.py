# # Trip recording: Whisper (local) → Qwen via Ollama HTTP → gTTS summary audio
import os
import requests
from faster_whisper import WhisperModel
from gtts import gTTS

# # Whisper small model — CPU int8 for manage.py runserver laptops
model = WhisperModel("base", device="cpu", compute_type="int8")

# ---------------- TRANSCRIBE ----------------
def transcribe_audio(file_path):
    if not os.path.exists(file_path):
        return "", None

    segments, info = model.transcribe(file_path, beam_size=5)
    text = " ".join([seg.text.strip() for seg in segments])
    lang = info.language if info else "unknown"

    return text.strip(), lang


# ---------------- QWEN (OLLAMA) ----------------
def translate_with_qwen(text):
    if not text:
        return ""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5",
                "prompt": f"Translate this into clear English:\n{text}",
                "stream": False
            }
        )
        return response.json().get("response", text)

    except Exception as e:
        print("OLLAMA ERROR:", e)
        return text


# ---------------- TEXT → AUDIO ----------------
def generate_audio(text, filepath):
    if not text:
        return None

    tts = gTTS(text=text, lang='en')
    tts.save(filepath)
    return filepath