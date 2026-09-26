import { useEffect, useState } from 'react'
import { api } from '../../api/client'

const STATS = [
  ['totalEmployees', 'Total employees'],
  ['activeEmployees', 'Active employees'],
  ['presentToday', 'Present today'],
  ['onLeaveToday', 'On leave today'],
  ['estimatedAbsentToday', 'Estimated absent'],
  ['pendingLeaveRequests', 'Pending leave requests'],
  ['pendingTaskReviews', 'Pending task reviews'],
]

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/admin/dashboard').then(setStats).catch((err) => setError(err.message))
  }, [])

  return (
    <div>
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
        </div>
      )}
    </div>
  )
}
