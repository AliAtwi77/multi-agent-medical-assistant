#tts.py
from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from backend.utils.exceptions import VoiceProcessingError
from backend.config.settings import ELEVENSLABS_VOICE_ID, ELEVENSLABS_TTS_MODEL

load_dotenv()
elevenlabs_api_key= os.getenv("ELEVENLABS_API_KEY")

def _get_client()->ElevenLabs:
    if not elevenlabs_api_key:
        raise VoiceProcessingError("ELEVENLABS_API_KEY is not Found")
    client= ElevenLabs(api_key=elevenlabs_api_key)
    return client

def synthesize_speech(text:str) -> bytes:
    if not text or not text.strip():
        raise VoiceProcessingError("Text for speech synthesis cannot be empty.")
    try:
        client= _get_client()
        audio_stream= client.text_to_speech.convert(
            voice_id="SAz9YHcvj6GT2YYXdXww",
            model_id=ELEVENSLABS_TTS_MODEL,
            text=text,
            output_format="mp3_44100_128",
        )
        return b"".join(audio_stream)
    except Exception as e:
        raise VoiceProcessingError(f"Text-to-Speech failed: {e}") from e


