import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import StatusPill from '../../components/StatusPill'

function greeting(hour) {
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [now, setNow] = useState(new Date())
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/employee/dashboard')
      setData(res)
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleCheckIn() {
    setBusy(true)
    setError('')
    try {
      await api.post('/api/employee/attendance/checkin')
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function handleCheckOut() {
    setBusy(true)
    setError('')
    try {
      await api.post('/api/employee/attendance/checkout')
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const today = data?.today
  const hasCheckedIn = Boolean(today?.checkIn)
  const hasCheckedOut = Boolean(today?.checkOut)

  return (
    <div>
      <div className="page-header">
        <h1>{greeting(now.getHours())}, {user?.name?.split(' ')[0] || 'there'} 👋</h1>
        <div className="clock">{now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })} · {now.toLocaleTimeString()}</div>
      </div>

      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="panel-title">
          <h2>Today</h2>
          {today && <StatusPill status={today.status} />}
        </div>
        <div className="grid-3" style={{ marginBottom: 16 }}>
          <div className="stat">
            <div className="value">{today?.checkIn ? today.checkIn.slice(11, 16) : '—'}</div>
            <div className="label">Check-in</div>
          </div>
          <div className="stat">
            <div className="value">{today?.checkOut ? today.checkOut.slice(11, 16) : '—'}</div>
            <div className="label">Check-out</div>
          </div>
          <div className="stat">
            <div className="value">{today?.workingHours || '—'}</div>
            <div className="label">Working hours so far</div>
          </div>
        </div>
        <div className="toolbar">
          <button className="btn btn-primary" onClick={handleCheckIn} disabled={busy || hasCheckedIn}>Check In</button>
          <button className="btn btn-secondary" onClick={handleCheckOut} disabled={busy || !hasCheckedIn || hasCheckedOut}>Check Out</button>
          <button className="btn btn-secondary" onClick={() => navigate('/leave?new=1')}>Apply Leave</button>
          <button className="btn btn-secondary" onClick={() => navigate('/tasks?new=1')}>Submit Task</button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title"><h2>Recent activity</h2></div>
        {data?.recentActivity?.length ? (
          <table>
            <tbody>
              {data.recentActivity.map((a, i) => (
                <tr key={i}>
                  <td style={{ width: '70%' }}>{a.label}</td>
                  <td style={{ color: 'var(--muted)', fontSize: 13 }}>
                    {a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">Nothing to show yet — check in or submit a task to get started.</div>
        )}
      </div>
    </div>
  )
}
