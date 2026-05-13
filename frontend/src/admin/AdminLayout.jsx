import { NavLink, Outlet } from 'react-router-dom'

export default function AdminLayout() {
  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <h2>Admin</h2>
        <NavLink to="/admin/age-bands">Age bands</NavLink>
        <NavLink to="/admin/courses">Courses</NavLink>
        <NavLink to="/admin/units">Units</NavLink>
        <NavLink to="/admin/skills">Skills</NavLink>
        <NavLink to="/admin/exercises">Exercises</NavLink>
      </aside>
      <main className="admin-main"><Outlet /></main>
    </div>
  )
}
