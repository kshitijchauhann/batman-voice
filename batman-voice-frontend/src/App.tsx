import { useState, useRef, useEffect, type KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura"
import { useTheme } from "@/components/theme-provider"
import type { AgentState } from "@livekit/components-react"

const BACKEND_WS = "ws://localhost:8000"

type AppState = "idle" | "thinking" | "speaking"

function mapToAgentState(s: AppState): AgentState {
  if (s === "thinking") return "thinking"
  if (s === "speaking") return "speaking"
  return "idle"
}

export function App() {
  const { resolvedTheme } = useTheme()

  const [prompt, setPrompt] = useState("")
  const [response, setResponse] = useState("")
  const [appState, setAppState] = useState<AppState>("idle")

  const wsRef = useRef<WebSocket | null>(null)
  const responseRef = useRef<HTMLDivElement>(null)

  // Audio plumbing
  const audioCtxRef = useRef<AudioContext | null>(null)
  const audioQueueRef = useRef<ArrayBuffer[]>([])
  const isPlayingRef = useRef(false)
  const audioDoneRef = useRef(false) // all chunks received from server

  // Auto-scroll response box
  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight
    }
  }, [response])

  // ── Audio helpers ────────────────────────────────────────────────────────────

  function getCtx(): AudioContext {
    if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
      audioCtxRef.current = new AudioContext()
    }
    if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume()
    }
    return audioCtxRef.current
  }

  async function playNextChunk() {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return
    isPlayingRef.current = true

    const ctx = getCtx()
    // .slice(0) is needed because decodeAudioData detaches the buffer
    const buf = audioQueueRef.current.shift()!.slice(0)

    try {
      const decoded = await ctx.decodeAudioData(buf)
      const src = ctx.createBufferSource()
      src.buffer = decoded
      src.connect(ctx.destination)
      src.onended = () => {
        isPlayingRef.current = false
        if (audioQueueRef.current.length > 0) {
          playNextChunk()
        } else if (audioDoneRef.current) {
          setAppState("idle")
        }
      }
      src.start()
    } catch (e) {
      console.error("Audio decode error:", e)
      isPlayingRef.current = false
      // Try next chunk even on error
      if (audioQueueRef.current.length > 0) playNextChunk()
      else if (audioDoneRef.current) setAppState("idle")
    }
  }

  function enqueueAudio(data: ArrayBuffer) {
    audioQueueRef.current.push(data)
    playNextChunk()
  }

  // ── Send message ─────────────────────────────────────────────────────────────

  async function sendMessage() {
    const text = prompt.trim()
    if (!text || appState !== "idle") return

    setPrompt("")
    setResponse("")
    setAppState("thinking")

    // Reset audio state
    audioQueueRef.current = []
    isPlayingRef.current = false
    audioDoneRef.current = false

    // Create AudioContext on user gesture to satisfy browser autoplay policy
    getCtx()

    const ws = new WebSocket(`${BACKEND_WS}/ws/chat`)
    wsRef.current = ws

    let firstChunk = true

    ws.onopen = () => {
      ws.send(JSON.stringify({ prompt: text }))
    }

    ws.onmessage = async (event: MessageEvent) => {
      if (event.data instanceof Blob) {
        // Binary frame = WAV audio chunk
        const buf = await event.data.arrayBuffer()
        enqueueAudio(buf)
        return
      }

      const msg = JSON.parse(event.data as string) as
        | { type: "text"; data: string }
        | { type: "done" }

      if (msg.type === "text") {
        if (firstChunk) {
          setAppState("speaking")
          firstChunk = false
        }
        setResponse((prev) => prev + msg.data)
      } else if (msg.type === "done") {
        // All audio chunks have been sent from server
        audioDoneRef.current = true
        // If no audio is queued / playing, go idle immediately
        if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
          setAppState("idle")
        }
      }
    }

    ws.onerror = (e) => {
      console.error("WebSocket error", e)
      setAppState("idle")
    }

    ws.onclose = () => {
      wsRef.current = null
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function handleStop() {
    wsRef.current?.close()
    wsRef.current = null
    audioQueueRef.current = []
    audioDoneRef.current = true
    setAppState("idle")
  }

  const agentState = mapToAgentState(appState)

  return (
    <div className="flex min-h-svh flex-col items-center justify-between p-6">
      {/* Visualizer */}
      <div className="flex flex-1 items-center justify-center w-full">
        <AgentAudioVisualizerAura
          size="xl"
          color="#1FD5F9"
          colorShift={0.3}
          state={agentState}
          themeMode={resolvedTheme}
          className="aspect-square size-auto w-full max-w-[448px]"
          audioTrack={undefined}
        />
      </div>

      {/* State label */}
      <p className="mb-2 font-mono text-xs text-muted-foreground tracking-widest uppercase">
        {appState}
      </p>

      {/* Response box */}
      {response && (
        <div
          ref={responseRef}
          className="mb-4 max-h-40 w-full max-w-xl overflow-y-auto rounded-md border bg-muted/40 px-4 py-3 font-mono text-sm leading-relaxed"
        >
          {response}
        </div>
      )}

      {/* Input bar */}
      <div className="flex w-full max-w-xl items-center gap-2 border-t pt-4">
        <Input
          placeholder="Ask Batman..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={appState !== "idle"}
          className="flex-1"
        />
        {appState === "idle" ? (
          <Button onClick={sendMessage} disabled={!prompt.trim()}>
            Send
          </Button>
        ) : (
          <Button variant="destructive" onClick={handleStop}>
            Stop
          </Button>
        )}
      </div>

      <p className="mt-2 font-mono text-xs text-muted-foreground">
        (Press <kbd>d</kbd> to toggle dark mode)
      </p>
    </div>
  )
}

export default App
