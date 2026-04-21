from langdetect import detect, LangDetectException
from typing import Optional

LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta"
}

class LanguageDetector:
    def __init__(self):
        pass
    
    def detect(self, text: str) -> str:
        try:
            detected = detect(text)
            return LANG_MAP.get(detected, "en")
        except LangDetectException:
            return "en"

_language_detector: Optional[LanguageDetector] = None

def get_language_detector() -> LanguageDetector:
    global _language_detector
    if _language_detector is None:
        _language_detector = LanguageDetector()
    return _language_detector
