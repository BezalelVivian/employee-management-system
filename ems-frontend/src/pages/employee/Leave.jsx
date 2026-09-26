import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'

const LEAVE_TYPES = ['Sick Leave', 'Casual Leave', 'Emergency Leave', 'Permission']
const STATUS_OPTIONS = ['Pending', 'Approved', 'Rejected']

const emptyForm = { leaveType: 'Casual Leave', fromDate: '', toDate: '', reason: '' }

export default function Leave() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [leaves, setLeaves] = useState([])
  const [filters, setFilters] = useState({ search: '', status: '', leave_type: '', date_from: '', date_to: '' })
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/employee/leave', filters)
      setLeaves(res)
    } catch (err) { setError(err.message) }
  }, [filters])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setForm(emptyForm)
      setShowForm(true)
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await api.post('/api/employee/leave', {
        leave_type: form.leaveType, from_date: form.fromDate, to_date: form.toDate, reason: form.reason,
      })
      setShowForm(false)
      await load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header"><h1>Leave</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <input
            className="search-input" placeholder="Search reason…"
            value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={filters.leave_type} onChange={(e) => setFilters({ ...filters, leave_type: e.target.value })}>
            <option value="">All types</option>
            {LEAVE_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>From</label>
            <input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>To</label>
            <input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
          </div>
          <button className="btn btn-primary" onClick={() => { setForm(emptyForm); setFormError(''); setShowForm(true) }}>Apply Leave</button>
        </div>

        <div className="table-wrap">
          {leaves.length ? (
            <table>
              <thead><tr><th>Type</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Admin remarks</th></tr></thead>
              <tbody>
                {leaves.map((l) => (
                  <tr key={l.id}>
                    <td>{l.leaveType}</td>
                    <td>{l.fromDate}</td>
                    <td>{l.toDate}</td>
                    <td>{l.reason}</td>
                    <td><StatusPill status={l.status} /></td>
                    <td>{l.adminRemarks || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No leave requests match these filters.</div>
          )}
        </div>
      </div>

      {showForm && (
        <Modal title="Apply for leave" onClose={() => setShowForm(false)}>
          {formError && <div className="banner banner-error">{formError}</div>}
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Leave type</label>
              <select value={form.leaveType} onChange={(e) => setForm({ ...form, leaveType: e.target.value })}>
                {LEAVE_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div className="field-row">
              <div className="field">
                <label>From</label>
                <input type="date" required value={form.fromDate} onChange={(e) => setForm({ ...form, fromDate: e.target.value })} />
              </div>
              <div className="field">
                <label>To</label>
                <input type="date" required value={form.toDate} onChange={(e) => setForm({ ...form, toDate: e.target.value })} />
              </div>
            </div>
            <div className="field">
              <label>Reason</label>
              <textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Submitting…' : 'Submit request'}</button>
          </form>
        </Modal>
      )}
    </div>
  )
}