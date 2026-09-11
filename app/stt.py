"""
Streaming Speech-to-Text using Google Cloud Speech.
Feeds audio chunks in as they arrive from the telephony WebSocket and
fires a callback whenever an utterance is finalized (end-of-speech detected).
"""

import asyncio
import logging
from typing import Callable, Awaitable

from google.cloud import speech

logger = logging.getLogger("voicebot.stt")


class GoogleStreamingSTT:
    def __init__(self, language_code: str = "en-IN", sample_rate_hz: int = 8000):
        self.client = speech.SpeechAsyncClient()
        self.language_code = language_code
        self.sample_rate_hz = sample_rate_hz

    def _streaming_config(self) -> speech.StreamingRecognitionConfig:
        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,  # matches telephony audio
            sample_rate_hertz=self.sample_rate_hz,
            language_code=self.language_code,
            model="phone_call",       # tuned for telephony audio quality
            use_enhanced=True,
            enable_automatic_punctuation=True,
        )
        return speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=True,
            single_utterance=False,
        )

    async def stream(
        self,
        audio_queue: asyncio.Queue,
        on_final_transcript: Callable[[str], Awaitable[None]],
    ):
        """
        Consumes raw audio bytes from audio_queue (None = end of stream) and
        calls on_final_transcript(text) each time Google marks a result final.
        """

        async def request_generator():
            yield speech.StreamingRecognizeRequest(streaming_config=self._streaming_config())
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            responses = await self.client.streaming_recognize(requests=request_generator())
            async for response in responses:
                for result in response.results:
                    if result.is_final:
                        transcript = result.alternatives[0].transcript
                        await on_final_transcript(transcript)
                    # else: interim result — hook here if you want live partials
                    # (e.g. for a "user is speaking" indicator or barge-in detection)
        except Exception:
            logger.exception("STT stream error")
