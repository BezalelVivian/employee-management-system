import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import StatusPill from '../../components/StatusPill'
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
  const [holidays, setHolidays] = useState([])
  const [party, setParty] = useState(0)

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
  useEffect(() => { api.get('/api/employee/holidays').then((h) => setHolidays(Array.isArray(h) ? h.slice(0, 3) : [])).catch(() => setHolidays([])) }, [])

  async function handleCheckIn() {
    setBusy(true)
    setError('')
    try {
      await api.post('/api/employee/attendance/checkin')
      setParty((n) => n + 1)
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

      <div className="panel">
        <div className="panel-title">
          <h2>Today</h2>
          {today && <StatusPill status={today.status} />}
        </div>
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
        )}
      </div>
    </div>
  )
}