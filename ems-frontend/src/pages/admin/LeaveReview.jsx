import { useEffect, useState, useCallback } from 'react'
<<<<<<< HEAD
import { fmtDate } from '../../utils/time'
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'

const STATUS_OPTIONS = ['Pending', 'Approved', 'Rejected']

export default function LeaveReview() {
  const [leaves, setLeaves] = useState([])
  const [error, setError] = useState('')
  const [reviewing, setReviewing] = useState(null)
  const [status, setStatus] = useState('Approved')
  const [remarks, setRemarks] = useState('')
  const [saving, setSaving] = useState(false)
  const [reviewError, setReviewError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      const data = await api.get('/api/admin/leaves')
      // Pending reviews first, so the admin's queue isn't buried under old ones.
      data.sort((a, b) => (a.Status === 'Pending') === (b.Status === 'Pending') ? 0 : a.Status === 'Pending' ? -1 : 1)
      setLeaves(data)
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { load() }, [load])

  function openReview(leave) {
    setStatus(leave.Status === 'Pending' ? 'Approved' : leave.Status)
    setRemarks(leave.AdminRemarks || '')
    setReviewError('')
    setReviewing(leave)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setReviewError('')
    try {
      await api.patch(`/api/admin/leaves/${reviewing.ID}/review`, { status, admin_remarks: remarks })
      setReviewing(null)
      await load()
    } catch (err) {
      setReviewError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header"><h1>Leave Review</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="table-wrap">
          {leaves.length ? (
            <table>
              <thead><tr><th>Employee</th><th>Type</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {leaves.map((l) => (
                  <tr key={l.ID}>
                    <td>{l.EmployeeName}</td>
                    <td>{l.LeaveType}</td>
<<<<<<< HEAD
                    <td>{fmtDate(l.FromDate)}</td>
                    <td>{fmtDate(l.ToDate)}</td>
=======
                    <td>{l.FromDate}</td>
                    <td>{l.ToDate}</td>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
                    <td>{l.Reason}</td>
                    <td><StatusPill status={l.Status} /></td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => openReview(l)}>
                        {l.Status === 'Pending' ? 'Review' : 'Edit review'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No leave requests submitted yet.</div>
          )}
        </div>
      </div>

      {reviewing && (
        <Modal title={`Review: ${reviewing.LeaveType}`} onClose={() => setReviewing(null)}>
          {reviewError && <div className="banner banner-error">{reviewError}</div>}
          <p style={{ fontSize: 14 }}>
<<<<<<< HEAD
            {reviewing.EmployeeName} · {fmtDate(reviewing.FromDate)} to {fmtDate(reviewing.ToDate)}
=======
            {reviewing.EmployeeName} · {reviewing.FromDate} to {reviewing.ToDate}
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
            {reviewing.Reason ? <> — "{reviewing.Reason}"</> : null}
          </p>
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Decision</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Remarks</label>
              <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save review'}</button>
          </form>
        </Modal>
      )}
    </div>
  )
}