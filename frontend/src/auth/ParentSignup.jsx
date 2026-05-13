import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api.js'
import { useAuthStore } from '../lib/store.js'

export default function ParentSignup() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await authApi.register({ email, password, full_name: fullName })
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'sign-up failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <h1>Create parent account</h1>
        <label>Full name (optional)
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </label>
        <label>Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>Password (min 8 chars)
          <input type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div className="auth-error">{error}</div>}
        <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
        <p className="auth-foot">Already registered? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  )
}
