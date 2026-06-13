# # Admin ticket TTS — edge-tts neural voices mapped to driver language codes
import asyncio
import edge_tts
import os
import sys
import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

VOICE_MAP = {
    'kn': 'kn-IN-GaganNeural',
    'ta': 'ta-IN-PallaviNeural',
    'hi': 'hi-IN-MadhurNeural',
    'en': 'en-US-JennyNeural'
}

async def _generate_audio(text, lang_code):
    voice = VOICE_MAP.get(lang_code, 'en-US-JennyNeural')
    comm = edge_tts.Communicate(text, voice)
    data = b''
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            data += chunk["data"]
    return data

def generate_voice_note(text, lang_code):
    if not text:
        return None
    # Proactor default on Windows can break libraries using aiohttp-style transports
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        audio = asyncio.run(_generate_audio(text, lang_code))
    except Exception:
        logger.exception("TTS (edge-tts) failed for lang=%s", lang_code)
        return None
    if not audio:
        return None
    filename = f"{uuid.uuid4()}.mp3"
    folder = os.path.join(settings.MEDIA_ROOT, 'voice_notes')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, 'wb') as f:
        f.write(audio)
    return f"{settings.MEDIA_URL}voice_notes/{filename}"