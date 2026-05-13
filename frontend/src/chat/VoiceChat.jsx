import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '../lib/api.js'
import { connectVoiceWs } from '../lib/ws.js'
import VisualizationRenderer from '../viz/VisualizationRenderer.jsx'

const SILENCE_THRESHOLD = 0.01
const SILENCE_DURATION_MS = 1500
const MIN_RECORDING_MS = 600

export default function VoiceChat() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('idle') // idle | recording | processing | speaking
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState(null)
  const [vizSpec, setVizSpec] = useState(null)
  const [ttsStartedAt, setTtsStartedAt] = useState(null)
  const [metrics, setMetrics] = useState(null)

  const wsRef = useRef(null)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const ctxRef = useRef(null)
  const analyserRef = useRef(null)
  const rafRef = useRef(null)
  const silenceStartRef = useRef(null)
  const recordStartRef = useRef(null)
  const statusRef = useRef('idle')
  const reqIdRef = useRef(null)
  const audioCtxRef = useRef(null)
  const audioQueueRef = useRef({}) // seq -> {chunks: Uint8Array[], meta}
  const audioPlayingRef = useRef(0)

  useEffect(() => { statusRef.current = status }, [status])

  // Connect WS once
  useEffect(() => {
    const token = auth.getChildToken()
    if (!token) { navigate('/select-child'); return }
    const ws = connectVoiceWs({
      token,
      handlers: {
        onVizSpec: (spec) => setVizSpec(spec),
        onTtsStart: () => {
          setStatus('speaking')
          setTtsStartedAt(performance.now())
        },
        onAudioMeta: (m) => {
          audioQueueRef.current[m.seq] = { chunks: [], meta: m, ended: false }
          setMessages((prev) => [
            ...prev,
            { id: `${reqIdRef.current}-clause-${m.seq}`, role: 'assistant', text: m.text },
          ])
        },
        onAudioChunk: (seq, buf) => {
          const slot = audioQueueRef.current[seq]
          if (slot) slot.chunks.push(new Uint8Array(buf))
        },
        onAudioEnd: (m) => {
          const slot = audioQueueRef.current[m.seq]
          if (!slot) return
          slot.ended = true
          playClause(m.seq)
        },
        onTurnComplete: (m) => {
          setMetrics(m.metrics)
          setStatus('idle')
          if (m.hy_text_in) {
            setMessages((prev) => [
              { id: `${m.request_id}-user`, role: 'user', text: m.hy_text_in },
              ...prev,
            ])
          }
        },
        onError: (e) => setError(typeof e === 'string' ? e : 'connection error'),
        onClose: () => {/* keep ui */},
      },
    })
    wsRef.current = ws
    return () => ws.close()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function ensureAudioCtx() {
    if (!audioCtxRef.current) audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
    return audioCtxRef.current
  }

  async function playClause(seq) {
    // Wait our turn (sequential playback).
    while (audioPlayingRef.current !== seq) {
      await new Promise((r) => setTimeout(r, 20))
    }
    const slot = audioQueueRef.current[seq]
    if (!slot) return
    const blob = new Blob(slot.chunks, { type: slot.meta.mime || 'audio/mpeg' })
    const arr = await blob.arrayBuffer()
    const ctx = ensureAudioCtx()
    try {
      const buf = await ctx.decodeAudioData(arr)
      const src = ctx.createBufferSource()
      src.buffer = buf
      src.connect(ctx.destination)
      src.start()
      await new Promise((resolve) => { src.onended = resolve })
    } catch {
      // Fallback: play via HTMLAudioElement.
      const url = URL.createObjectURL(blob)
      const a = new Audio(url)
      await a.play().catch(() => {})
      await new Promise((r) => { a.onended = r; a.onerror = r })
      URL.revokeObjectURL(url)
    }
    audioPlayingRef.current = seq + 1
  }

  const teardownAudio = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    analyserRef.current = null
    silenceStartRef.current = null
    setAudioLevel(0)
  }, [])

  const finish = useCallback(() => {
    if (mediaRef.current?.state === 'recording') mediaRef.current.stop()
    else setStatus('processing')
    teardownAudio()
  }, [teardownAudio])

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
            finish()
            return
          }
        } else {
          silenceStartRef.current = null
        }
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    tick()
  }, [finish])

  async function startRecording() {
    if (!wsRef.current) return
    try {
      setError(null); setVizSpec(null); setMetrics(null)
      audioQueueRef.current = {}
      audioPlayingRef.current = 0

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
        ? 'audio/webm;codecs=opus' : 'audio/webm'
      const rec = new MediaRecorder(stream, { mimeType: mime })
      mediaRef.current = rec
      chunksRef.current = []
      reqIdRef.current = crypto.randomUUID()
      wsRef.current.start(reqIdRef.current)

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      rec.onstop = async () => {
        setStatus('processing')
        if (chunksRef.current.length) {
          const blob = new Blob(chunksRef.current, { type: mime })
          const buf = await blob.arrayBuffer()
          wsRef.current.sendAudio(buf)
        }
        wsRef.current.endUtterance(reqIdRef.current)
      }
      rec.start(200)
      recordStartRef.current = Date.now()
      silenceStartRef.current = null
      setStatus('recording')
      monitor()
    } catch {
      setError('Microphone access denied. Please allow it and reload.')
      teardownAudio()
      setStatus('idle')
    }
  }

  function handleMicClick() {
    if (status === 'recording') finish()
    else if (status === 'idle') startRecording()
  }

  return (
    <div className="voice-screen">
      <div className="viz-pane">
        <VisualizationRenderer spec={vizSpec} ttsStartedAt={ttsStartedAt} />
      </div>
      <div className="chat-pane">
        <div className="messages">
          {messages.length === 0 && status === 'idle' && (
            <div className="empty">Tap the mic and ask a math question.</div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`msg msg-${m.role}`}>
              <div className="msg-bubble">{m.text}</div>
            </div>
          ))}
          {status === 'recording' && <div className="status-line"><span className="dot-pulse" /> Listening…</div>}
          {status === 'processing' && <div className="status-line"><span className="spinner" /> Thinking…</div>}
          {status === 'speaking' && <div className="status-line"><span className="dot-pulse" /> Speaking…</div>}
          {error && <div className="error-toast">{error}</div>}
        </div>
        <footer className="toolbar">
          <button
            className={`btn-mic${status === 'recording' ? ' active' : ''}`}
            onClick={handleMicClick}
            disabled={status === 'processing'}
          >
            {status === 'recording'
              ? <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
              : <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>}
          </button>
          <div className="glow" style={{'--lvl': audioLevel}} />
        </footer>
        {metrics && (
          <div className="metrics-footer">
            e2e {metrics.e2e_ms}ms · tts {metrics.tts_total_ms}ms · ttfb {metrics.tts_first_byte_ms ?? '—'}ms
          </div>
        )}
      </div>
    </div>
  )
}
