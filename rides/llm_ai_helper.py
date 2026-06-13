# # Human-style admin → driver wording via Ollama qwen2.5:7b (fallback: Google Translate)
import ollama
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    'kn': 'Kannada',
    'ta': 'Tamil',
    'hi': 'Hindi',
    'en': 'English',
}

def get_natural_translation(admin_message, driver_lang_code):
    """
    Translate using Ollama (Qwen) first. If fails, fallback to Google Translate.
    """
    if not admin_message or driver_lang_code not in LANGUAGE_MAP:
        return admin_message

    target_lang = LANGUAGE_MAP[driver_lang_code]

    # Ollama prompt designed for natural, spoken language
    prompt = f"""You are a friendly driver speaking {target_lang}.
The admin sent this message: "{admin_message}"
Rewrite it in {target_lang} exactly as you would say it to a fellow driver.
Use everyday words, short sentences, warm tone.
Output ONLY the {target_lang} sentence.
Your response:"""

    try:
        response = ollama.chat(
            model='qwen2.5:7b',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.7, 'num_predict': 200}
        )
        translated = response['message']['content'].strip()
        # Basic validation: should not be empty or too short
        if translated and len(translated) > 5:
            return translated
        else:
            logger.warning(f"Ollama output too short: {translated}")
    except Exception as e:
        logger.error(f"Ollama error: {e}")

    # Fallback to Google Translate
    try:
        dest = driver_lang_code  # 'kn', 'ta', 'hi'
        return GoogleTranslator(source='en', target=dest).translate(admin_message)
    except Exception as e:
        logger.error(f"Google Translate fallback error: {e}")
        return admin_message