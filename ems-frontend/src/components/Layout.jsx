import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const EMPLOYEE_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/profile', label: 'My Profile' },
  { to: '/attendance', label: 'Attendance' },
  { to: '/tasks', label: 'Tasks' },
  { to: '/leave', label: 'Leave' },
]

const ADMIN_LINKS = [
  { to: '/admin/dashboard', label: 'Dashboard' },
  { to: '/admin/employees', label: 'Employees' },
  { to: '/admin/tasks', label: 'Task Review' },
  { to: '/admin/leaves', label: 'Leave Review' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const links = user?.role === 'admin' ? ADMIN_LINKS : EMPLOYEE_LINKS

  // Close the mobile drawer whenever the route changes (e.g. after tapping a link).
  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  // Prevent the page behind the drawer from scrolling while it's open on mobile.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <header className="mobile-topbar">
        <button
          className="icon-btn menu-btn"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          aria-expanded={menuOpen}
        >
          <span /><span /><span />
        </button>
        <div className="mobile-topbar-brand">EMS</div>
        <div className="mobile-topbar-spacer" aria-hidden="true" />
      </header>

      <div
        className={`sidebar-backdrop ${menuOpen ? 'is-visible' : ''}`}
        onClick={() => setMenuOpen(false)}
        aria-hidden="true"
      />

      <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
        <div className="sidebar-top">
          <div>
            <div className="sidebar-brand">EMS</div>
            <div className="sidebar-role">{user?.role === 'admin' ? 'Admin' : 'Employee'}</div>
          </div>
          <button className="icon-btn sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Close menu">
            ✕
          </button>
        </div>
        <nav className="sidebar-nav">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-user">
          <div className="sidebar-user-name">{user?.name}</div>
          <button className="sidebar-logout" onClick={handleLogout}>Log out</button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}