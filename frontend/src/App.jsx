import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = import.meta.env.DEV ? '' : '' // use Vite proxy in dev

export default function App() {
  const [apiStatus, setApiStatus] = useState(null)
  const [apiMessage, setApiMessage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchApi() {
      try {
        const res = await fetch(`${API_BASE}/api/`)
        const data = await res.json()
        setApiMessage(data.message ?? 'OK')
        setApiStatus(res.ok ? 'ok' : 'error')
      } catch (e) {
        setError(e.message)
        setApiStatus('error')
      } finally {
        setLoading(false)
      }
    }
    fetchApi()
  }, [])

  return (
    <main className="page">
      <h1>Teacher Agents</h1>
      <p className="tagline">Frontend + FastAPI</p>
      <section className="api-card">
        <h2>API status</h2>
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && (
          <p className={apiStatus === 'ok' ? 'success' : 'error'}>
            {apiStatus === 'ok' ? apiMessage : 'Request failed'}
          </p>
        )}
      </section>
    </main>
  )
}
