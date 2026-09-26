import { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'

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
            <input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>To</label>
            <input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              <option>Present</option>
              <option>Late</option>
              <option>Absent</option>
              <option>On Leave</option>
              <option>Holiday</option>
              <option>Weekly Off</option>
            </select>
          </div>
        </div>

        <div className="table-wrap">
          {rows.length ? (
            <table>
              <thead>
                <tr><th>Date</th><th>Check-in</th><th>Check-out</th><th>Working hours</th><th>Status</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.date}>
                    <td>{r.date}</td>
                    <td>{r.checkIn ? r.checkIn.slice(11, 16) : '—'}</td>
                    <td>{r.checkOut ? r.checkOut.slice(11, 16) : '—'}</td>
                    <td>{r.workingHours || '—'}</td>
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