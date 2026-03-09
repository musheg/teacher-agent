import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

const SILENCE_THRESHOLD = 0.01
const SILENCE_DURATION_MS = 1500
const MIN_RECORDING_MS = 600

export default function App() {
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('idle')
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState(null)

  const chatIdRef = useRef(crypto.randomUUID())
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const ctxRef = useRef(null)
  const analyserRef = useRef(null)
  const rafRef = useRef(null)
  const silenceStartRef = useRef(null)
  const recordStartRef = useRef(null)
  const statusRef = useRef('idle')
  const bottomRef = useRef(null)

  useEffect(() => { statusRef.current = status }, [status])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, status])

  const teardown = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    analyserRef.current = null
    mediaRecorderRef.current = null
    silenceStartRef.current = null
  }, [])

  useEffect(() => teardown, [teardown])

  const sendAudio = useCallback(async (blob) => {
    setStatus('processing')
    setAudioLevel(0)
    try {
      const fd = new FormData()
      fd.append('audio', blob, 'recording.webm')
      fd.append('chat_id', chatIdRef.current)

      const res = await fetch('/api/chat', { method: 'POST', body: fd })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()

      setMessages(prev => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: 'Voice message' },
        { id: crypto.randomUUID(), role: 'assistant', content: data.response },
      ])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setStatus('idle')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null

    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    } else {
      setStatus('idle')
    }

    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    analyserRef.current = null
    silenceStartRef.current = null
    setAudioLevel(0)
  }, [])

  const monitor = useCallback(() => {
    const analyser = analyserRef.current
    if (!analyser) return
    const buf = new Float32Array(analyser.fftSize)

    const tick = () => {
      if (statusRef.current !== 'recording') return
      analyser.getFloatTimeDomainData(buf)

      let sum = 0
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i]
      const rms = Math.sqrt(sum / buf.length)
      setAudioLevel(Math.min(1, rms * 5))

      const elapsed = Date.now() - recordStartRef.current
      if (elapsed > MIN_RECORDING_MS) {
        if (rms < SILENCE_THRESHOLD) {
          if (!silenceStartRef.current) silenceStartRef.current = Date.now()
          else if (Date.now() - silenceStartRef.current > SILENCE_DURATION_MS) {
            stopRecording()
            return
          }
        } else {
          silenceStartRef.current = null
        }
      }

      rafRef.current = requestAnimationFrame(tick)
    }
    tick()
  }, [stopRecording])

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
      streamRef.current = stream

      const audioCtx = new AudioContext()
      ctxRef.current = audioCtx
      const src = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 2048
      src.connect(analyser)
      analyserRef.current = analyser

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mime })
        if (blob.size > 0) sendAudio(blob)
        else setStatus('idle')
      }

      recorder.start(100)
      recordStartRef.current = Date.now()
      silenceStartRef.current = null
      setStatus('recording')
      monitor()
    } catch {
      setError('Microphone access denied. Please allow microphone access and reload.')
      teardown()
      setStatus('idle')
    }
  }, [sendAudio, monitor, teardown])

  const handleMicClick = useCallback(() => {
    if (status === 'recording') stopRecording()
    else if (status === 'idle') startRecording()
  }, [status, startRecording, stopRecording])

  const handleNewChat = useCallback(() => {
    if (status === 'recording') stopRecording()
    chatIdRef.current = crypto.randomUUID()
    setMessages([])
    setError(null)
    setStatus('idle')
  }, [status, stopRecording])

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        {status === 'recording' ? (
          <div className="live-badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M2 12h2M6 8v8M10 4v16M14 8v8M18 6v12M22 10v4" />
            </svg>
            Live
          </div>
        ) : (
          <span className="header-title">Teacher Agents</span>
        )}

        {messages.length > 0 && (
          <button className="btn-icon btn-new" onClick={handleNewChat} aria-label="New conversation">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        )}
      </header>

      {/* ── Messages ── */}
      <div className="messages">
        {messages.length === 0 && status === 'idle' && (
          <div className="empty">
            <svg className="empty-mic" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
            <p>Tap the microphone to start talking</p>
          </div>
        )}

        {messages.map(m => (
          <div key={m.id} className={`msg msg-${m.role}`}>
            <div className="msg-bubble">{m.content}</div>
          </div>
        ))}

        {status === 'recording' && (
          <div className="status-line">
            <span className="dot-pulse" />
            Listening…
          </div>
        )}
        {status === 'processing' && (
          <div className="status-line">
            <span className="spinner" />
            Processing…
          </div>
        )}

        {error && <div className="error-toast">{error}</div>}
        <div ref={bottomRef} />
      </div>

      {/* ── Glow ── */}
      <div
        className={`glow${status === 'recording' ? ' glow-on' : ''}`}
        style={{ '--lvl': audioLevel }}
      />

      {/* ── Toolbar ── */}
      <footer className="toolbar">
        <button
          className={`btn-mic${status === 'recording' ? ' active' : ''}`}
          onClick={handleMicClick}
          disabled={status === 'processing'}
          aria-label={status === 'recording' ? 'Stop recording' : 'Start recording'}
        >
          {status === 'recording' ? (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>
      </footer>
    </div>
  )
}
