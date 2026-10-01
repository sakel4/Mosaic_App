"""Stream microphone audio to the local Amazon Transcribe WebSocket."""
import argparse
import asyncio
import json

import sounddevice as sd
from websockets.asyncio.client import connect

SAMPLE_RATE = 16000
BLOCK_SIZE = 1600


async def run(url: str, device: int | None) -> None:
    loop = asyncio.get_running_loop()
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=32)

    def enqueue_audio(chunk: bytes) -> None:
        try:
            audio_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            print("Audio buffer full; dropping a chunk.")

    def audio_callback(indata, frames, timing, status) -> None:
        loop.call_soon_threadsafe(enqueue_audio, bytes(indata))

    async with connect(url) as websocket:
        async def send_audio() -> None:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    await websocket.send("end")
                    return
                await websocket.send(chunk)

        async def receive_transcripts() -> None:
            async for message in websocket:
                try:
                    event = json.loads(message)
                except json.JSONDecodeError:
                    print(message)
                    continue
                kind = event.get("type", "transcript")
                print(f"[{kind}] {event.get('text', '')}", flush=True)

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_transcripts())
        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                channels=1,
                dtype="int16",
                device=device,
                callback=audio_callback,
            ):
                print(f"Streaming microphone audio to {url}. Press Enter to stop.")
                await asyncio.to_thread(input)
        finally:
            await audio_queue.put(None)
            await sender
            await receiver


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:8000/ws/transcribe")
    parser.add_argument("--device", type=int, help="Microphone device index")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    try:
        asyncio.run(run(args.url, args.device))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
