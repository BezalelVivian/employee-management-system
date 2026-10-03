import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import StatusPill from '../../components/StatusPill'
<<<<<<< HEAD
import Icon from '../../components/Icon'
import { fmtTime, fmtDateTime, fmtDate } from '../../utils/time'

function Confetti() {
  const bits = Array.from({ length: 26 }, (_, i) => i)
  const colors = ['#e8620c', '#ff9a55', '#ffd2b0', '#231d18', '#cf5509']
  return (
    <div className="confetti" aria-hidden="true">
      {bits.map((i) => (
        <i key={i} style={{ '--x': `${(Math.random() - 0.5) * 340}px`, '--y': `${-80 - Math.random() * 200}px`, '--r': `${Math.random() * 720}deg`, background: colors[i % colors.length], animationDelay: `${Math.random() * 120}ms` }} />
      ))}
    </div>
  )
}

function HoursCard({ today, finished }) {
  const live = Boolean(today?.inProgress)
  return (
    <div className="hours-card">
      <div className="hours-label">{live && <span className="live-dot" aria-hidden="true" />}{finished ? 'Worked today' : 'Worked so far'}</div>
      <div className="hours-value">{today?.workingHours || '—'}</div>
      <div className="hours-sub">{live ? 'Currently checked in' : finished ? 'Checked out for the day' : 'Not checked in yet'}</div>
    </div>
  )
}
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

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
<<<<<<< HEAD
  const [holidays, setHolidays] = useState([])
  const [party, setParty] = useState(0)
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

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
<<<<<<< HEAD
  useEffect(() => { api.get('/api/employee/holidays').then((h) => setHolidays(Array.isArray(h) ? h.slice(0, 3) : [])).catch(() => setHolidays([])) }, [])
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

  async function handleCheckIn() {
    setBusy(true)
    setError('')
    try {
      await api.post('/api/employee/attendance/checkin')
<<<<<<< HEAD
      setParty((n) => n + 1)
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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
<<<<<<< HEAD
      {party > 0 && <Confetti key={party} />}
      <div className="page-header hero">
        <div>
          <h1>{greeting(now.getHours())}, {user?.name?.split(' ')[0] || 'there'}</h1>
          <div className="clock">
            <Icon name="calendar" size={14} />
            {now.toLocaleDateString('en-GB', { weekday: 'long' })}, {fmtDate(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`)}
          </div>
        </div>
        <div className="hero-time" aria-label="Current time">{now.toLocaleTimeString()}</div>
      </div>

      {error && <div className="banner banner-error" role="alert">{error}</div>}
=======
      <div className="page-header">
        <h1>{greeting(now.getHours())}, {user?.name?.split(' ')[0] || 'there'} 👋</h1>
        <div className="clock">{now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })} · {now.toLocaleTimeString()}</div>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

      <div className="panel">
        <div className="panel-title">
          <h2>Today</h2>
          {today && <StatusPill status={today.status} />}
        </div>
<<<<<<< HEAD
        <div className="today-grid">
          <HoursCard today={today} finished={hasCheckedOut} />
          <div className="grid-2">
            <div className="stat">
              <span className="stat-icon"><Icon name="login" size={18} /></span>
              <div className="value">{today?.checkIn ? fmtTime(today.checkIn) : '—'}</div>
              <div className="label">Check-in</div>
            </div>
            <div className="stat">
              <span className="stat-icon"><Icon name="logout" size={18} /></span>
              <div className="value">{today?.checkOut ? fmtTime(today.checkOut) : '—'}</div>
              <div className="label">Check-out</div>
            </div>
          </div>
        </div>
        <div className="toolbar">
          <button className="btn btn-primary" onClick={handleCheckIn} disabled={busy || hasCheckedIn}><Icon name="login" size={16} />Check In</button>
          <button className="btn btn-secondary" onClick={handleCheckOut} disabled={busy || !hasCheckedIn || hasCheckedOut}><Icon name="logout" size={16} />Check Out</button>
          <button className="btn btn-secondary" onClick={() => navigate('/leave?new=1')}><Icon name="sun" size={16} />Apply Leave</button>
          <button className="btn btn-secondary" onClick={() => navigate('/tasks?new=1')}><Icon name="plus" size={16} />Submit Task</button>
        </div>
      </div>

      {holidays.length > 0 && (
        <div className="panel holiday-panel">
          <div className="panel-title"><h2>Upcoming holidays</h2></div>
          <ul className="holiday-list">
            {holidays.map((h) => (
              <li key={h.date}>
                <span className="holiday-date">{fmtDate(h.date)}</span>
                <span className="holiday-name">{h.name}</span>
                <span className={`holiday-left ${h.daysLeft <= 3 ? 'is-soon' : ''}`}>{h.daysLeft === 0 ? 'Today' : h.daysLeft === 1 ? 'Tomorrow' : `in ${h.daysLeft} days`}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="panel">
        <div className="panel-title"><h2>Recent activity</h2></div>
        {data?.recentActivity?.length ? (
          <ul className="activity-list">
            {data.recentActivity.map((a, i) => (
              <li key={i}>
                <span className="activity-dot" aria-hidden="true" />
                <span className="activity-label">{a.label}</span>
                <span className="activity-time">
                  {fmtDateTime(a.timestamp)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <Icon name="activity" size={28} />
            <div>Nothing to show yet — check in or submit a task to get started.</div>
          </div>
=======
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
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
        )}
      </div>
    </div>
  )
<<<<<<< HEAD
}
=======
}
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
