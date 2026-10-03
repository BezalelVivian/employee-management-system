import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
<<<<<<< HEAD
import Icon from './Icon'
import Avatar from './Avatar'
import { useNotifications, NotificationBell, NotificationsModal } from './Notifications'

const EMPLOYEE_LINKS = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/profile', label: 'My Profile', icon: 'user' },
  { to: '/attendance', label: 'Attendance', icon: 'clock' },
  { to: '/tasks', label: 'Tasks', icon: 'tasks' },
  { to: '/leave', label: 'Leave', icon: 'sun' },
]

const ADMIN_LINKS = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/admin/employees', label: 'Employees', icon: 'users' },
  { to: '/admin/attendance', label: 'Attendance', icon: 'clock' },
  { to: '/admin/tasks', label: 'Task Review', icon: 'tasks' },
  { to: '/admin/leaves', label: 'Leave Review', icon: 'calendar' },
  { to: '/admin/holidays', label: 'Holidays', icon: 'flag' },
]

export default function Layout() {
  const { user, logout, photo, refreshPhoto } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const isAdmin = user?.role === 'admin'
  const links = isAdmin ? ADMIN_LINKS : EMPLOYEE_LINKS
  const [notesOpen, setNotesOpen] = useState(false)
  // Notifications and photos belong to employee records; admin accounts have neither.
  const notifs = useNotifications(!isAdmin, location.pathname)

  // Sync the employee's own photo from the server once per page load (cached copy shows first).
  useEffect(() => { if (!isAdmin) refreshPhoto() }, [isAdmin, refreshPhoto])
=======

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
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

  // Close the mobile drawer whenever the route changes (e.g. after tapping a link).
  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  // Prevent the page behind the drawer from scrolling while it's open on mobile.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

<<<<<<< HEAD
  // Let Escape close the drawer.
  useEffect(() => {
    if (!menuOpen) return undefined
    const onKey = (e) => { if (e.key === 'Escape') setMenuOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [menuOpen])

=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
<<<<<<< HEAD
      <a className="skip-link" href="#main">Skip to content</a>

=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
      <header className="mobile-topbar">
        <button
          className="icon-btn menu-btn"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          aria-expanded={menuOpen}
        >
<<<<<<< HEAD
          <Icon name="menu" size={22} />
        </button>
        <div className="mobile-topbar-brand"><span className="wordmark">EMS</span></div>
        <div className="mobile-topbar-spacer" aria-hidden="true" />
        {!isAdmin && <NotificationBell unread={notifs.unread} onClick={() => setNotesOpen(true)} />}
        <Avatar name={user?.name} src={isAdmin ? null : photo} size="sm" />
=======
          <span /><span /><span />
        </button>
        <div className="mobile-topbar-brand">EMS</div>
        <div className="mobile-topbar-spacer" aria-hidden="true" />
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
      </header>

      <div
        className={`sidebar-backdrop ${menuOpen ? 'is-visible' : ''}`}
        onClick={() => setMenuOpen(false)}
        aria-hidden="true"
      />

      <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
        <div className="sidebar-top">
          <div>
<<<<<<< HEAD
            <div className="sidebar-brand"><span className="wordmark">EMS</span></div>
            <div className={`sidebar-role ${isAdmin ? 'is-admin' : ''}`}>
              <Icon name={isAdmin ? 'shield' : 'briefcase'} size={12} />
              {isAdmin ? 'Admin workspace' : 'Employee workspace'}
            </div>
          </div>
          <button className="icon-btn sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Close menu">
            <Icon name="close" size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <Icon name={l.icon} size={18} />
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-user">
          <div className="sidebar-user-card">
            <Avatar name={user?.name} src={isAdmin ? null : photo} />
            <div className="sidebar-user-meta">
              <div className="sidebar-user-name">{user?.name}</div>
              <div className="sidebar-user-role">{isAdmin ? 'Administrator' : 'Employee'}</div>
            </div>
            {!isAdmin && <NotificationBell className="bell-sidebar" unread={notifs.unread} onClick={() => setNotesOpen(true)} />}
          </div>
          <button className="sidebar-logout" onClick={handleLogout}>
            <Icon name="logout" size={16} />
            Log out
          </button>
        </div>
      </aside>

      <main className="main-content" id="main" tabIndex={-1}>
        <div className="page-enter" key={location.pathname}>
          <Outlet />
        </div>
      </main>

      {notesOpen && !isAdmin && (
        <NotificationsModal
          notes={notifs.notes} unread={notifs.unread}
          markRead={notifs.markRead} markAllRead={notifs.markAllRead}
          onClose={() => setNotesOpen(false)}
        />
      )}
=======
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
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
    </div>
  )
}