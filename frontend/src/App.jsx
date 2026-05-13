import { useEffect } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import './App.css'

import Login from './auth/Login.jsx'
import ParentSignup from './auth/ParentSignup.jsx'
import ChildPicker from './auth/ChildPicker.jsx'
import VoiceChat from './chat/VoiceChat.jsx'
import ParentDashboard from './parent/Dashboard.jsx'
import AdminLayout from './admin/AdminLayout.jsx'
import { AgeBandsPage, CoursesPage, ExercisesPage, SkillsPage, UnitsPage } from './admin/pages.jsx'
import { AdminGuard, ChildGuard, ParentGuard } from './RouteGuards.jsx'
import { useAuthStore } from './lib/store.js'

function Shell({ children }) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">Teacher Agents</Link>
        <nav>
          {user && <Link to="/select-child">Learn</Link>}
          {user && <Link to="/parent">Parent</Link>}
          {user?.role === 'admin' && <Link to="/admin/age-bands">Admin</Link>}
          {user && <button className="link" onClick={() => { logout(); navigate('/login') }}>Sign out</button>}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  )
}

function Home() {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="home">
      <h1>Welcome back{user.full_name ? `, ${user.full_name}` : ''}.</h1>
      <div className="home-actions">
        <Link className="cta" to="/select-child">Start a learning session</Link>
        <Link className="cta secondary" to="/parent">Open parent dashboard</Link>
      </div>
    </div>
  )
}

export default function App() {
  const refresh = useAuthStore((s) => s.refresh)
  useEffect(() => { refresh() }, [refresh])
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<ParentSignup />} />

          <Route element={<ParentGuard />}>
            <Route path="/" element={<Home />} />
            <Route path="/select-child" element={<ChildPicker />} />
            <Route path="/parent" element={<ParentDashboard />} />
          </Route>

          <Route element={<ChildGuard />}>
            <Route path="/learn" element={<VoiceChat />} />
          </Route>

          <Route element={<AdminGuard />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin/age-bands" element={<AgeBandsPage />} />
              <Route path="/admin/courses" element={<CoursesPage />} />
              <Route path="/admin/units" element={<UnitsPage />} />
              <Route path="/admin/skills" element={<SkillsPage />} />
              <Route path="/admin/exercises" element={<ExercisesPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}
