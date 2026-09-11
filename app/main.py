"""
Voice Bot - FastAPI entrypoint
Handles the telephony provider's WebSocket media stream (Exotel/Ozonetel/Twilio-compatible
payload format), pipes audio to Google STT (streaming), sends the transcript to the dialogue
engine (Claude), converts the reply to speech, and streams audio back to the caller.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import base64
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.stt import GoogleStreamingSTT
from app.dialogue import DialogueEngine
from app.tts import synthesize_speech
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicebot")

app = FastAPI(title="Voice Bot")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    Telephony provider connects here and streams audio frames as JSON events.
    Adjust the event parsing in `parse_provider_event` to match your provider's
    exact payload (Exotel, Ozonetel, and Twilio all differ slightly).
    """
    await websocket.accept()
    logger.info("Call connected")

    stt = GoogleStreamingSTT(language_code=settings.default_language)
    dialogue = DialogueEngine()

    audio_queue: asyncio.Queue = asyncio.Queue()
    stt_task = asyncio.create_task(stt.stream(audio_queue, on_final_transcript=lambda text: handle_turn(
        text, websocket, dialogue
    )))

    try:
        while True:
            raw = await websocket.receive_text()
            event = parse_provider_event(raw)

            if event["type"] == "media":
                await audio_queue.put(event["audio_bytes"])
            elif event["type"] == "start":
                logger.info("Stream started: %s", event.get("stream_sid"))
            elif event["type"] == "stop":
                logger.info("Stream stopped")
                break

    except WebSocketDisconnect:
        logger.info("Call disconnected")
    finally:
        await audio_queue.put(None)  # signal STT stream to close
        stt_task.cancel()


async def handle_turn(transcript: str, websocket: WebSocket, dialogue: DialogueEngine):
    """Called every time STT finalizes an utterance. Runs dialogue + TTS and streams audio back."""
    if not transcript.strip():
        return

    logger.info("User said: %s", transcript)
    reply_text = await dialogue.get_response(transcript)
    logger.info("Bot reply: %s", reply_text)

    audio_bytes = await synthesize_speech(reply_text, language_code=settings.default_language)
    await send_audio_to_caller(websocket, audio_bytes)


def parse_provider_event(raw_message: str) -> dict:
    """
    Normalize provider-specific WebSocket payloads into a common shape.
    NOTE: This is a Twilio-style example. Update field names for Exotel/Ozonetel
    per their media streaming docs before going live.
    """
    data = json.loads(raw_message)
    event_type = data.get("event")

    if event_type == "media":
        payload_b64 = data["media"]["payload"]
        return {"type": "media", "audio_bytes": base64.b64decode(payload_b64)}
    elif event_type == "start":
        return {"type": "start", "stream_sid": data.get("start", {}).get("streamSid")}
    elif event_type == "stop":
        return {"type": "stop"}
    return {"type": "unknown"}


async def send_audio_to_caller(websocket: WebSocket, audio_bytes: bytes):
    """
    Wrap synthesized audio back into the provider's expected media-stream format
    and send it over the same WebSocket. Format/encoding must match what the
    provider expects (commonly base64 mu-law/8kHz).
    """
    payload_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    message = {
        "event": "media",
        "media": {"payload": payload_b64},
    }
    await websocket.send_text(json.dumps(message))
