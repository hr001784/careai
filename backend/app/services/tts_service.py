from gtts import gTTS
import io
from typing import Optional

class TTSService:
    def __init__(self):
        self.lang_map = {
            "en": "en",
            "hi": "hi",
            "ta": "ta"
        }
    
    async def synthesize(self, text: str, language: str = "en") -> bytes:
        try:
            lang_code = self.lang_map.get(language, "en")
            # Create TTS object
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer.read()
        except Exception as e:
            print(f"TTS Synthesis error: {e}")
            # Return an empty byte stream or a small silence if gTTS fails
            return b""

_tts_service: Optional[TTSService] = None

def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
