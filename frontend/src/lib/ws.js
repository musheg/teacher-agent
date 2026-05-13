// Voice WebSocket client.
//
// Connects to /api/ws/session?token=<child_jwt>.
// Sends audio chunks as binary; emits start/end_utterance JSON envelopes.
// Receives viz_spec, audio_meta, audio chunks, audio_end, turn_complete events.

export function connectVoiceWs({ token, handlers }) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${window.location.host}/api/ws/session?token=${encodeURIComponent(token)}`
  const ws = new WebSocket(url)
  ws.binaryType = 'arraybuffer'

  let pendingAudioSeq = null

  ws.onmessage = (evt) => {
    if (typeof evt.data === 'string') {
      const msg = JSON.parse(evt.data)
      switch (msg.type) {
        case 'viz_spec':
          handlers.onVizSpec?.(msg.payload?.spec ?? msg.spec ?? msg.payload)
          break
        case 'tts_started':
          handlers.onTtsStart?.()
          break
        case 'audio_meta':
          pendingAudioSeq = msg.seq
          handlers.onAudioMeta?.(msg)
          break
        case 'audio_end':
          pendingAudioSeq = null
          handlers.onAudioEnd?.(msg)
          break
        case 'turn_complete':
          handlers.onTurnComplete?.(msg)
          break
        case 'error':
          handlers.onError?.(msg.detail || 'unknown error')
          break
        default:
          handlers.onEvent?.(msg)
      }
    } else if (pendingAudioSeq !== null) {
      handlers.onAudioChunk?.(pendingAudioSeq, evt.data)
    }
  }
  ws.onclose = (e) => handlers.onClose?.(e)
  ws.onerror = (e) => handlers.onError?.(e?.message || 'websocket error')

  return {
    socket: ws,
    start(requestId) {
      ws.send(JSON.stringify({ type: 'start', request_id: requestId }))
    },
    sendAudio(buf) {
      if (ws.readyState === WebSocket.OPEN) ws.send(buf)
    },
    endUtterance(requestId) {
      ws.send(JSON.stringify({ type: 'end_utterance', request_id: requestId }))
    },
    close() {
      try { ws.send(JSON.stringify({ type: 'close' })) } catch (e) { /* noop */ }
      ws.close()
    },
  }
}
