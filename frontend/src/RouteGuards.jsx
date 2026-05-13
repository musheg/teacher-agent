import { useEffect } from 'react'
import { Navigate, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from './lib/store.js'
import { auth } from './lib/api.js'

export function ParentGuard() {
  const { user, loading } = useAuthStore()
  if (loading) return <div className="loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'parent' && user.role !== 'admin') return <Navigate to="/login" replace />
  return <Outlet />
}

export function AdminGuard() {
  const { user, loading } = useAuthStore()
  if (loading) return <div className="loading">Loading…</div>
  if (!user || user.role !== 'admin') return <Navigate to="/login" replace />
  return <Outlet />
}

export function ChildGuard() {
  const navigate = useNavigate()
  const token = auth.getChildToken()
  useEffect(() => {
    if (!token) navigate('/select-child', { replace: true })
  }, [token, navigate])
  if (!token) return null
  return <Outlet />
}
