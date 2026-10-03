import { useEffect, useState, useCallback } from 'react'
import DateInput from '../../components/DateInput'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'
import { fmtTime, fmtDate, fmtTimeInput, todayLocalISO } from '../../utils/time'

const STATUS_OPTIONS = ['Present', 'Half Day', 'Short Hours', 'Missing Check-out', 'Absent', 'On Leave', 'Holiday', 'Weekly Off']

export default function AdminAttendance() {
  const today = todayLocalISO()
  const [filters, setFilters] = useState({ date_from: today, date_to: today, status: '', search: '' })
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ checkIn: '', checkOut: '' })
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/admin/attendance', { date_from: filters.date_from, date_to: filters.date_to })
      setRows(res)
    } catch (err) { setError(err.message) }
  }, [filters.date_from, filters.date_to])

  useEffect(() => { load() }, [load])

  const visible = rows.filter((r) => {
    if (filters.status && r.status !== filters.status) return false
    if (filters.search && !`${r.employeeName} ${r.employeeCode}`.toLowerCase().includes(filters.search.toLowerCase())) return false
    return true
  })

  function openEdit(r) {
    setForm({ checkIn: fmtTimeInput(r.checkIn), checkOut: fmtTimeInput(r.checkOut) })
    setEditError('')
    setEditing(r)
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setEditError('')
    try {
      await api.put('/api/admin/attendance', {
        employee_id: editing.employeeId,
        attendance_date: editing.date,
        check_in: form.checkIn,
        check_out: form.checkOut || null,
      })
      setEditing(null)
      await load()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header"><h1>Attendance</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>From</label>
            <DateInput max={today} value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>To</label>
            <DateInput max={today} value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Employee</label>
            <input className="search-input" placeholder="Search name or code" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
          </div>
        </div>
        <p className="hint-text" style={{ marginTop: 0 }}>
          Up to 31 days at a time. Use Edit to fix a forgotten check-in or check-out — the working hours are recalculated automatically.
        </p>

        <div className="table-wrap">
          {visible.length ? (
            <table>
              <thead>
                <tr><th>Date</th><th>Employee</th><th>Check-in</th><th>Check-out</th><th>Working hours</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr key={`${r.date}-${r.employeeId}`}>
                    <td>{fmtDate(r.date)}</td>
                    <td>{r.employeeName}{r.employeeCode ? <span style={{ marginLeft: 6, fontSize: 12.5, color: 'var(--muted)' }}>{r.employeeCode}</span> : null}</td>
                    <td>{r.checkIn ? fmtTime(r.checkIn) : '—'}</td>
                    <td>{r.checkOut ? fmtTime(r.checkOut) : (r.inProgress ? 'Working…' : '—')}</td>
                    <td>{r.workingHours ? `${r.workingHours}${r.inProgress ? ' so far' : ''}` : '—'}</td>
                    <td><StatusPill status={r.status} /></td>
                    <td><button className="btn btn-secondary btn-sm" onClick={() => openEdit(r)}>Edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No attendance records match these filters.</div>
          )}
        </div>
      </div>

      {editing && (
        <Modal title={`Edit attendance — ${editing.employeeName}`} onClose={() => setEditing(null)}>
          {editError && <div className="banner banner-error">{editError}</div>}
          <form onSubmit={handleSave}>
            <p className="hint-text" style={{ marginTop: 0 }}>{fmtDate(editing.date)}</p>
            <div className="field-row">
              <div className="field">
                <label>Check-in</label>
                <input type="time" required value={form.checkIn} onChange={(e) => setForm({ ...form, checkIn: e.target.value })} />
              </div>
              <div className="field">
                <label>Check-out</label>
                <input type="time" value={form.checkOut} onChange={(e) => setForm({ ...form, checkOut: e.target.value })} />
                <p className="hint-text">Leave empty if they haven't checked out.</p>
              </div>
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </form>
        </Modal>
      )}
    </div>
  )
}
