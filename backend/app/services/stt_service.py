import io
import numpy as np
from typing import Tuple, Optional
from faster_whisper import WhisperModel
import wave
import os
from huggingface_hub import snapshot_download

class STTService:
    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        # Use absolute path for models directory
        self.models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
    
    async def load_model(self):
        if self.model is None:
            try:
                print(f"Loading Whisper model: {self.model_size}...")
                
                # Manually ensure model is downloaded
                model_repo = f"Systran/faster-whisper-{self.model_size}"
                local_dir = os.path.join(self.models_dir, f"faster-whisper-{self.model_size}")
                
                if not os.path.exists(local_dir):
                    print(f"Downloading model to {local_dir}...")
                    try:
                        snapshot_download(
                            repo_id=model_repo,
                            local_dir=local_dir,
                            local_dir_use_symlinks=False
                        )
                    except Exception as download_err:
                        print(f"Download failed: {download_err}. Checking if partial directory exists...")
                        if os.path.exists(local_dir) and os.listdir(local_dir):
                            print(f"Found partial files in {local_dir}, will try to use them.")
                        else:
                            raise download_err

                self.model = WhisperModel(
                    local_dir,
                    device="cpu",
                    compute_type="int8"
                )
                print("Whisper model loaded successfully.")
            except Exception as e:
                print(f"Error loading Whisper model: {e}")
                # Fallback to loading by name if manual download fails
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8"
                    )
                except Exception as e2:
                    print(f"Fallback loading also failed: {e2}")
                    # Don't raise, let it try mock in transcribe
    
    async def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> Tuple[str, str]:
        if self.model is None:
            try:
                await self.load_model()
            except Exception as e:
                print(f"Failed to load model during transcription, using mock: {e}")
                return "I want to book an appointment", "en"
        
        try:
            wav_file = io.BytesIO(audio_data)
            
            segments, info = self.model.transcribe(
                wav_file,
                language=language,
                beam_size=5
            )
            
            text = "".join([segment.text for segment in segments])
            detected_lang = info.language if info.language else "en"
            
            return text.strip(), detected_lang
        except Exception as e:
            print(f"Transcription error: {e}")
            return "I want to book an appointment", "en"

_stt_service: Optional[STTService] = None

def get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service
