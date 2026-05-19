# Batman Voice Assistant

A real-time voice assistant web application that responds to your questions with the cold, calculated, and tactical persona of Batman.

The application consists of:
- **Backend (`batman-voice-backend`)**: A Python FastAPI service that uses Ollama to generate text responses and PyTorch-based TTS to synthesize speech.
- **Frontend (`batman-voice-frontend`)**: A React/TypeScript application built with Vite and Tailwind CSS.

---

## Prerequisites

Before running the application, make sure you have the following installed:
- **Python 3.10+** (for the backend)
- **Node.js 20+** and **pnpm** (for the frontend)
- **Ollama** (for local LLM inference)

### Setup Ollama
You need Ollama running locally with the specific model used by this app.
Run the following command to pull and serve the model:
```bash
ollama run gemma3:1b-it-qat
```

*(Note: Keep the Ollama server running in the background while using the app.)*

---

## Running the Application

You will need to open two terminal windows to run both the backend and frontend simultaneously.

### 1. Start the Backend

Open a terminal and navigate to the backend directory:

```bash
cd batman-voice-backend
```

Create and activate a Python virtual environment:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate
# Or on Windows:
# .venv\Scripts\activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

Start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
*The backend is now running and accepting WebSocket connections at `ws://localhost:8000/ws/chat`.*

---

### 2. Start the Frontend

Open a second terminal window and navigate to the frontend directory:

```bash
cd batman-voice-frontend
```

Install the dependencies using `pnpm`:
```bash
pnpm install
```

Start the development server:
```bash
pnpm dev
```

### 3. Open the App
Navigate to `http://localhost:5173` in your web browser. Type your query, press Send, and prepare for Batman's response.
