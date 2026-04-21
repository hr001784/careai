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
        lang_code = self.lang_map.get(language, "en")
        tts = gTTS(text=text, lang=lang_code, slow=False)
        
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return audio_buffer.read()

_tts_service: Optional[TTSService] = None

def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
