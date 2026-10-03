import { useEffect, useState } from 'react'
<<<<<<< HEAD
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import Icon from '../../components/Icon'

// tone: visual only. `to` makes the card a shortcut to an existing admin page.
const STATS = [
  { key: 'totalEmployees', label: 'Total employees', icon: 'users', tone: 'indigo' },
  { key: 'activeEmployees', label: 'Active employees', icon: 'briefcase', tone: 'indigo' },
  { key: 'presentToday', label: 'Present today', icon: 'check', tone: 'green' },
  { key: 'onLeaveToday', label: 'On leave today', icon: 'sun', tone: 'blue' },
  { key: 'estimatedAbsentToday', label: 'Estimated absent', icon: 'absent', tone: 'red' },
  { key: 'pendingLeaveRequests', label: 'Pending leave requests', icon: 'calendar', tone: 'amber', to: '/admin/leaves' },
  { key: 'pendingTaskReviews', label: 'Pending task reviews', icon: 'tasks', tone: 'amber', to: '/admin/tasks' },
=======
import { api } from '../../api/client'

const STATS = [
  ['totalEmployees', 'Total employees'],
  ['activeEmployees', 'Active employees'],
  ['presentToday', 'Present today'],
  ['onLeaveToday', 'On leave today'],
  ['estimatedAbsentToday', 'Estimated absent'],
  ['pendingLeaveRequests', 'Pending leave requests'],
  ['pendingTaskReviews', 'Pending task reviews'],
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
]

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/admin/dashboard').then(setStats).catch((err) => setError(err.message))
  }, [])

  return (
    <div>
<<<<<<< HEAD
      <div className="page-header">
        <h1>Admin Dashboard</h1>
        <div className="clock">Overview of your team today</div>
      </div>
      {error && <div className="banner banner-error" role="alert">{error}</div>}
      {!stats && !error && (
        <div className="grid-3">
          {STATS.map((s) => <div className="stat skeleton" key={s.key} aria-hidden="true" />)}
        </div>
      )}
      {stats && (
        <div className="grid-3">
          {STATS.map(({ key, label, icon, tone, to }) => {
            const inner = (
              <>
                <span className="stat-icon"><Icon name={icon} size={18} /></span>
                <div className="value">{stats[key]}</div>
                <div className="label">{label}</div>
                {to && <span className="stat-link">Review <Icon name="arrow" size={14} /></span>}
              </>
            )
            return to ? (
              <Link className={`stat stat-${tone} stat-clickable`} key={key} to={to}>{inner}</Link>
            ) : (
              <div className={`stat stat-${tone}`} key={key}>{inner}</div>
            )
          })}
=======
      <div className="page-header"><h1>Admin Dashboard</h1></div>
      {error && <div className="banner banner-error">{error}</div>}
      {stats && (
        <div className="grid-3">
          {STATS.map(([key, label]) => (
            <div className="stat" key={key}>
              <div className="value">{stats[key]}</div>
              <div className="label">{label}</div>
            </div>
          ))}
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
        </div>
      )}
    </div>
  )
<<<<<<< HEAD
}
=======
}
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
