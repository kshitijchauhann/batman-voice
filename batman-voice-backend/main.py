import asyncio
import concurrent.futures
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from services.llm import stream_batman_response
from services.tts import generate_audio_bytes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.1.6:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        prompt = data.get("prompt", "")

        loop = asyncio.get_event_loop()
        text_queue: asyncio.Queue = asyncio.Queue()
        audio_queue: asyncio.Queue = asyncio.Queue()

        def worker():
            """
            Runs in a background thread.
            - Streams LLM tokens → pushes each token to text_queue immediately
            - Submits TTS for each sentence to thread pool concurrently
            - As each TTS future completes (in sentence order), pushes WAV bytes
              to audio_queue WITHOUT waiting for the full LLM response to finish
            """
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
            buffer = ""
            pending: list[concurrent.futures.Future] = []

            def flush_ready_audio():
                """Push any futures that have already completed, in order."""
                while pending and pending[0].done():
                    fut = pending.pop(0)
                    try:
                        audio_bytes = fut.result()
                        loop.call_soon_threadsafe(audio_queue.put_nowait, audio_bytes)
                    except Exception as e:
                        print(f"TTS error: {e}")

            try:
                for token in stream_batman_response(prompt):
                    # Send text token to frontend immediately
                    loop.call_soon_threadsafe(text_queue.put_nowait, token)
                    buffer += token

                    # When we hit sentence-ending punctuation, kick off TTS
                    if any(c in buffer for c in ".!?"):
                        cleaned = buffer.strip()
                        buffer = ""
                        if cleaned:
                            pending.append(
                                executor.submit(generate_audio_bytes, cleaned)
                            )

                    # Opportunistically flush any completed TTS futures now
                    flush_ready_audio()

                # Handle any remaining text
                if buffer.strip():
                    pending.append(
                        executor.submit(generate_audio_bytes, buffer.strip())
                    )

            finally:
                # Signal text stream done
                loop.call_soon_threadsafe(text_queue.put_nowait, None)

                # Drain remaining pending audio futures in order
                for fut in pending:
                    try:
                        audio_bytes = fut.result()
                        loop.call_soon_threadsafe(audio_queue.put_nowait, audio_bytes)
                    except Exception as e:
                        print(f"TTS error: {e}")

                loop.call_soon_threadsafe(audio_queue.put_nowait, None)
                executor.shutdown(wait=False)

        threading.Thread(target=worker, daemon=True).start()

        # Run text relay and audio relay CONCURRENTLY so audio is sent
        # as soon as the first sentence is synthesised, not after all text is done.
        async def relay_text():
            while True:
                token = await text_queue.get()
                if token is None:
                    break
                await websocket.send_json({"type": "text", "data": token})

        async def relay_audio():
            while True:
                audio_bytes = await audio_queue.get()
                if audio_bytes is None:
                    break
                await websocket.send_bytes(audio_bytes)

        await asyncio.gather(relay_text(), relay_audio())

        await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
