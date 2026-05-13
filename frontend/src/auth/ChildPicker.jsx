import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth, authApi } from '../lib/api.js'

export default function ChildPicker() {
  const navigate = useNavigate()
  const [children, setChildren] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState({ display_name: '', birthdate: '', grade: '', locale: 'hy-AM' })
  const [error, setError] = useState(null)

  useEffect(() => {
    authApi.listChildren().then((rows) => {
      setChildren(rows)
      setShowNew(rows.length === 0)
    }).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])

  async function pick(child) {
    try {
      const { access_token } = await authApi.issueChildToken(child.id)
      auth.setChildToken(access_token)
      auth.setActiveChild(child.id)
      navigate('/learn')
    } catch (e) {
      setError(e.message)
    }
  }

  async function createChild(e) {
    e.preventDefault()
    setError(null)
    try {
      const payload = {
        display_name: form.display_name,
        birthdate: form.birthdate,
        grade: form.grade === '' ? null : Number(form.grade),
        locale: form.locale,
      }
      const c = await authApi.createChild(payload)
      setChildren((prev) => [...prev, c])
      setShowNew(false)
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <div className="auth-screen"><p>Loading…</p></div>

  return (
    <div className="auth-screen">
      <div className="auth-card wide">
        <h1>Who's learning today?</h1>
        {error && <div className="auth-error">{error}</div>}
        <div className="child-grid">
          {children.map((c) => (
            <button key={c.id} className="child-tile" onClick={() => pick(c)}>
              <div className="child-name">{c.display_name}</div>
              <div className="child-meta">Grade {c.grade ?? '—'}</div>
            </button>
          ))}
          <button className="child-tile add" onClick={() => setShowNew(true)}>
            <div className="child-name">+ Add child</div>
          </button>
        </div>
        {showNew && (
          <form className="auth-card inline" onSubmit={createChild}>
            <h2>Add a child profile</h2>
            <label>Display name
              <input required value={form.display_name} onChange={(e) => setForm({...form, display_name: e.target.value})} />
            </label>
            <label>Birthdate
              <input type="date" required value={form.birthdate} onChange={(e) => setForm({...form, birthdate: e.target.value})} />
            </label>
            <label>Grade
              <input type="number" min="0" max="12" value={form.grade} onChange={(e) => setForm({...form, grade: e.target.value})} />
            </label>
            <label>Locale
              <select value={form.locale} onChange={(e) => setForm({...form, locale: e.target.value})}>
                <option value="hy-AM">Armenian (hy-AM)</option>
                <option value="en-US">English (en-US)</option>
              </select>
            </label>
            <button type="submit">Save</button>
          </form>
        )}
      </div>
    </div>
  )
}
