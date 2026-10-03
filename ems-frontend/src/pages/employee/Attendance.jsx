import { useEffect, useState, useCallback } from 'react'
<<<<<<< HEAD
import DateInput from '../../components/DateInput'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import { fmtTime, fmtDate } from '../../utils/time'
=======
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

export default function Attendance() {
  const [rows, setRows] = useState([])
  const [filters, setFilters] = useState({ date_from: '', date_to: '', status: '' })
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/employee/attendance', filters)
      setRows(res)
    } catch (err) { setError(err.message) }
  }, [filters])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="page-header"><h1>Attendance History</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>From</label>
<<<<<<< HEAD
            <DateInput value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>To</label>
            <DateInput value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
=======
            <input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>To</label>
            <input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              <option>Present</option>
<<<<<<< HEAD
              <option>Half Day</option>
              <option>Short Hours</option>
              <option>Missing Check-out</option>
=======
              <option>Late</option>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
              <option>Absent</option>
              <option>On Leave</option>
              <option>Holiday</option>
              <option>Weekly Off</option>
            </select>
          </div>
        </div>

<<<<<<< HEAD
        <p className="hint-text" style={{ marginTop: 0 }}>
          Forgot to check out, or checked in late by mistake? Ask an admin to correct that day.
        </p>
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
        <div className="table-wrap">
          {rows.length ? (
            <table>
              <thead>
                <tr><th>Date</th><th>Check-in</th><th>Check-out</th><th>Working hours</th><th>Status</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.date}>
<<<<<<< HEAD
                    <td>{fmtDate(r.date)}</td>
                    <td>{r.checkIn ? fmtTime(r.checkIn) : '—'}</td>
                    <td>{r.checkOut ? fmtTime(r.checkOut) : (r.inProgress ? 'Working…' : '—')}</td>
                    <td>{r.workingHours ? `${r.workingHours}${r.inProgress ? ' so far' : ''}` : '—'}</td>
=======
                    <td>{r.date}</td>
                    <td>{r.checkIn ? r.checkIn.slice(11, 16) : '—'}</td>
                    <td>{r.checkOut ? r.checkOut.slice(11, 16) : '—'}</td>
                    <td>{r.workingHours || '—'}</td>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
                    <td><StatusPill status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No attendance records match these filters.</div>
          )}
        </div>
      </div>
    </div>
  )
}