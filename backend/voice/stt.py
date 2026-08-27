#stt.py
from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from backend.utils.exceptions import VoiceProcessingError
from backend.config.settings import ELEVENSLABS_VOICE_ID, ELEVENSLABS_STT_MODEL

load_dotenv()
elevenlabs_api_key= os.getenv("ELEVENLABS_API_KEY")

def _get_client()->ElevenLabs:
    if not elevenlabs_api_key:
        raise VoiceProcessingError("ELEVENLABS_API_KEY is not Found")
    client= ElevenLabs(api_key=elevenlabs_api_key)
    return client

def transcribe_audio(audio_bytes:bytes, filename:str= "audio.webm") -> str:
    try:
        client= _get_client()
        result= client.speech_to_text.convert(
            file=(filename, audio_bytes),
            model_id=ELEVENSLABS_STT_MODEL
        )
        text= getattr(result, "text", None) or (result.get("text") if isinstance(result,dict) else "")
        return text 
    except Exception as e:
        raise VoiceProcessingError(f"Speech-to-Text failed: {e}") from e
