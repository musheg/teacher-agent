import { useEffect, useState } from 'react'
import { parentApi } from '../lib/api.js'

export default function ParentDashboard() {
  const [children, setChildren] = useState([])
  const [selected, setSelected] = useState(null)
  const [mastery, setMastery] = useState([])
  const [stumbles, setStumbles] = useState([])
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => { parentApi.children().then(setChildren).catch((e) => setError(e.message)) }, [])

  useEffect(() => {
    if (!selected) return
    Promise.all([
      parentApi.mastery(selected),
      parentApi.stumbles(selected),
      parentApi.sessions(selected),
    ]).then(([m, s, ss]) => {
      setMastery(m); setStumbles(s); setSessions(ss)
    }).catch((e) => setError(e.message))
  }, [selected])

  return (
    <div className="parent-dash">
      <h1>Parent dashboard</h1>
      {error && <div className="auth-error">{error}</div>}
      <section className="kids">
        {children.map((c) => (
          <button key={c.id}
            className={`kid${selected === c.id ? ' selected' : ''}`}
            onClick={() => setSelected(c.id)}>
            <div className="kid-name">{c.display_name}</div>
            <div className="kid-week">{c.weekly_minutes} min this week</div>
          </button>
        ))}
      </section>

      {selected && (
        <div className="dash-grid">
          <section className="heatmap">
            <h2>Skill mastery</h2>
            <div className="heat-rows">
              {mastery.map((m) => (
                <div key={m.skill_code} className="heat-row">
                  <div className="heat-label">{m.skill_name}</div>
                  <div className="heat-bar"><div className="heat-fill" style={{width: `${(m.p_known * 100).toFixed(0)}%`}} /></div>
                  <div className="heat-pct">{Math.round(m.p_known * 100)}%</div>
                </div>
              ))}
              {mastery.length === 0 && <p>No mastery data yet.</p>}
            </div>
          </section>

          <section className="stumbles">
            <h2>Top stumbling blocks</h2>
            <ul>
              {stumbles.map((s) => (
                <li key={s.skill_code}>
                  <strong>{s.skill_name}</strong> — {s.failure_count} miss{s.failure_count === 1 ? '' : 'es'}
                </li>
              ))}
              {stumbles.length === 0 && <li>None yet — great job!</li>}
            </ul>
          </section>

          <section className="sessions">
            <h2>Recent sessions</h2>
            <table>
              <thead><tr><th>Started</th><th>Ended</th><th>Turns</th></tr></thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{new Date(s.started_at).toLocaleString()}</td>
                    <td>{s.ended_at ? new Date(s.ended_at).toLocaleString() : '—'}</td>
                    <td>{s.turn_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  )
}
