"""
Text-to-Speech using Google Cloud TTS.
Returns audio encoded to match the telephony provider's expected format
(mu-law/8kHz here — adjust to your provider).
"""

import logging
from google.cloud import texttospeech

logger = logging.getLogger("voicebot.tts")

_client = texttospeech.TextToSpeechAsyncClient()


async def synthesize_speech(text: str, language_code: str = "en-IN") -> bytes:
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MULAW,
        sample_rate_hertz=8000,
    )

    response = await _client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    return response.audio_content
