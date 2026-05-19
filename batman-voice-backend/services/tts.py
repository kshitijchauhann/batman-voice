import io
import wave

import numpy as np
from pocket_tts import TTSModel

print("Loading TTS model...")

tts_model = TTSModel.load_model()
voice_state = tts_model.get_state_for_audio_prompt("./final-batman.wav")

print("TTS ready.")


def generate_audio_bytes(text: str) -> bytes:
    """Generate audio for text and return as WAV bytes (for browser playback)."""
    audio = tts_model.generate_audio(voice_state, text)
    audio_np = audio.numpy()

    # Convert float32 → int16 PCM
    if audio_np.dtype != np.int16:
        audio_np = np.clip(audio_np, -1.0, 1.0)
        audio_np = (audio_np * 32767).astype(np.int16)

    if audio_np.ndim > 1:
        audio_np = audio_np.squeeze()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(tts_model.sample_rate)
        wf.writeframes(audio_np.tobytes())

    return buf.getvalue()
