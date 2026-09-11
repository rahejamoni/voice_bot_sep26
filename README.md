# Voice Bot — Starter Skeleton

Pipeline: **Telephony (WebSocket audio) → Google STT (streaming) → Claude (dialogue) → Google TTS → back to caller**

This is a working skeleton, not production-ready. It gets the plumbing right so you (or Claude Code)
can iterate on it fast.

## What's here

```
app/
  main.py       FastAPI WebSocket endpoint that the telephony provider connects to
  stt.py        Google Cloud Speech streaming wrapper
  dialogue.py   Claude-based conversation engine
  tts.py        Google Cloud TTS wrapper
  config.py     Env var config
requirements.txt
```

## Setup

1. **Install deps**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables**
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-service-account.json
   export DEFAULT_LANGUAGE=en-IN   # or hi-IN, etc.
   ```

3. **Google Cloud setup**
   - Enable the Speech-to-Text and Text-to-Speech APIs on your GCP project
   - Create a service account with those API roles, download the JSON key

4. **Run locally**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Expose it for your telephony provider** (during dev)
   ```bash
   ngrok http 8000
   ```
   Point Exotel/Ozonetel/Twilio's media-stream webhook at `wss://<your-ngrok-domain>/media-stream`.

## What you WILL need to adjust before this works end-to-end

1. **`parse_provider_event()` in `main.py`** — the payload shape is written Twilio-style.
   Exotel and Ozonetel have their own JSON structure for `start`/`media`/`stop` events —
   check their media streaming docs and match field names exactly.

2. **Audio encoding** — confirm what your telephony provider sends/expects. This skeleton
   assumes mu-law 8kHz (common for phone audio), matching Google STT/TTS's `MULAW` encoding.
   If your provider uses PCM16 or a different sample rate, update both `stt.py` and `tts.py`.

3. **Barge-in / interruption handling** — not implemented yet. When the caller starts speaking
   while the bot is still talking, you'll want to stop TTS playback. The `stt.py` interim-results
   loop has a comment marking where to hook this in.

4. **Call state / session management** — `DialogueEngine` currently holds history in memory per
   WebSocket connection, which is fine for one instance. For multiple server instances, move
   history to Redis keyed by call SID.

## Suggested next steps with Claude Code

Since you have Claude Code, a good way to move fast from here:

```
cd voicebot
claude
```
Then ask it to, e.g.:
- "Wire up Exotel's exact media-stream JSON format in main.py"
- "Add barge-in handling so the bot stops talking when the caller interrupts"
- "Add call logging to a database for QA/compliance"
- "Write a docker-compose setup for local dev with ngrok"

Claude Code can iterate directly against this codebase, run it, and debug based on real errors —
much faster than continuing to build it turn-by-turn in chat.
