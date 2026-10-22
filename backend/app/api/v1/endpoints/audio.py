from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.audio import AudioSpeechRequest, AudioSpeechResponse, AudioTranscriptionResponse
from app.services.voice_service import VoiceService, VoiceServiceError

router = APIRouter(prefix="/audio", tags=["audio"])

_MAX_AUDIO_UPLOAD_BYTES = 12 * 1024 * 1024


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> AudioTranscriptionResponse:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is required.")
    if len(payload) > _MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file exceeds size limit.")

    service = VoiceService()
    try:
        result = service.transcribe_audio(audio_bytes=payload, filename=file.filename or "voice-input.webm", language=language)
    except VoiceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AudioTranscriptionResponse(
        text=result.text,
        partial=result.text or "",
        final=result.text or "",
        language=result.language,
    )


@router.post("/speech", response_model=AudioSpeechResponse)
def synthesize_speech(payload: AudioSpeechRequest) -> AudioSpeechResponse:
    service = VoiceService()
    try:
        result = service.synthesize_speech(text=payload.text, language=payload.language, voice=payload.voice)
    except VoiceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AudioSpeechResponse(audio_base64=result.audio_base64, mime_type=result.mime_type)
