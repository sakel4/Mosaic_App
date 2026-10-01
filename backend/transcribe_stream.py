"""WebSocket endpoint: raw mic audio in, live Amazon Transcribe text out.

Client protocol:
  -> binary frames: PCM 16-bit little-endian, mono, 16 kHz
  -> text frame "end": stop and flush
  <- {"type": "partial" | "final", "text": "..."}
"""
import asyncio
import os

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

load_dotenv()  # boto/awscrt read AWS_* credentials from the process environment

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
LANGUAGE = os.getenv("TRANSCRIBE_LANGUAGE", "en-US")
SAMPLE_RATE = 16000

router = APIRouter()


class _Forwarder(TranscriptResultStreamHandler):
    def __init__(self, output_stream, websocket: WebSocket):
        super().__init__(output_stream)
        self._ws = websocket

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        for result in transcript_event.transcript.results:
            if not result.alternatives:
                continue
            await self._ws.send_json(
                {
                    "type": "partial" if result.is_partial else "final",
                    "text": result.alternatives[0].transcript,
                }
            )


@router.websocket("/ws/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    client = TranscribeStreamingClient(region=REGION)
    stream = await client.start_stream_transcription(
        language_code=LANGUAGE,
        media_sample_rate_hz=SAMPLE_RATE,
        media_encoding="pcm",
    )

    async def pump_audio():
        try:
            while True:
                message = await websocket.receive()
                if message.get("bytes"):
                    await stream.input_stream.send_audio_event(audio_chunk=message["bytes"])
                elif message.get("text") == "end" or message["type"] == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            await stream.input_stream.end_stream()

    forwarder = _Forwarder(stream.output_stream, websocket)
    try:
        await asyncio.gather(pump_audio(), forwarder.handle_events())
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass  # already closed
