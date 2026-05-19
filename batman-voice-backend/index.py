import queue
import threading

import sounddevice as sd
from ollama import chat
from pocket_tts import TTSModel

# =========================================================
# LOAD TTS ONCE
# =========================================================

tts_model = TTSModel.load_model()

voice_state = tts_model.get_state_for_audio_prompt("./final-batman.wav")

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
ROLE:
You are Batman-like tactical mentor.

BEHAVIOR RULES:
- concise
- cold
- calm
- strategic
- emotionally controlled
- no optimism
- no therapy language
- no supportive phrases
- no emojis
- no slang
- short sentences
- challenge excuses
- prioritize discipline
- prioritize action
- prioritize responsibility

FORBIDDEN PHRASES:
- "I'm here for you"
- "You are not alone"
- "Stay positive"
- "Everything will be okay"
- "I understand how you feel"

RESPONSE STYLE:
Bad:
"Don't worry. I'm here for you."

Good:
"Fear is expected. Inaction is unacceptable."

Good:
"Discipline matters more than motivation."

Keep replies under 20 words max.
"""

# =========================================================
# AUDIO QUEUE
# =========================================================

tts_queue = queue.Queue()

# =========================================================
# TTS WORKER
# =========================================================


def tts_worker():
    while True:
        text = tts_queue.get()

        if text is None:
            break

        try:
            audio = tts_model.generate_audio(voice_state, text)

            sd.play(audio.numpy(), samplerate=tts_model.sample_rate)

            sd.wait()

        except Exception as e:
            print("TTS Error:", e)

        tts_queue.task_done()


# Start background TTS thread
threading.Thread(target=tts_worker, daemon=True).start()

# =========================================================
# STREAMING CHAT
# =========================================================


def batman_chat(user_prompt):

    stream = chat(
        model="gemma3:1b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        options={
            "temperature": 0.2,
            "num_predict": 60,
        },
    )

    buffer = ""

    for chunk in stream:
        token = chunk["message"]["content"]

        print(token, end="", flush=True)

        buffer += token

        # SPEAK PER SENTENCE
        if "." in buffer or "!" in buffer or "?" in buffer:
            cleaned = buffer.strip()

            if cleaned:
                tts_queue.put(cleaned)

            buffer = ""

    # leftover text
    if buffer.strip():
        tts_queue.put(buffer.strip())


# =========================================================
# MAIN LOOP
# =========================================================

while True:
    user = input("\nYou: ")

    if user.lower() in ["exit", "quit"]:
        break

    print("\nBatman:", end=" ")

    batman_chat(user)
