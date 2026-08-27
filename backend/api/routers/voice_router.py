#voice_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Response

from backend.voice.stt import transcribe_audio
from backend.voice.tts import synthesize_speech
from backend.utils.exceptions import MedicalAssistantError
from backend.utils.logger import logger
from backend.api.models.schemas import TTSRequest


router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
)


@router.post("/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        text = transcribe_audio(audio_bytes, filename=file.filename or "audio.webm")
        return {"text": text}
    except MedicalAssistantError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception("Speech-to-text failed")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")



@router.post("/text-to-speech")
async def text_to_speech(
    payload: TTSRequest,
):
    try:
        audio_bytes = synthesize_speech(text=payload.text,)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
        )

    except Exception as e:
        logger.exception("Text-to-speech failed: {}", e)
        raise HTTPException(status_code=500,detail=f"Unexpected server error: {e}",)