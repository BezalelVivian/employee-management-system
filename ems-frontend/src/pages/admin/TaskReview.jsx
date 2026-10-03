import { useEffect, useState, useCallback } from 'react'
<<<<<<< HEAD
import { fmtDate } from '../../utils/time'
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'

const ADMIN_STATUS_OPTIONS = ['Pending', 'Approved', 'Needs Changes', 'Rejected']

export default function TaskReview() {
  const [tasks, setTasks] = useState([])
  const [error, setError] = useState('')
  const [reviewing, setReviewing] = useState(null)
  const [status, setStatus] = useState('Approved')
  const [remarks, setRemarks] = useState('')
  const [saving, setSaving] = useState(false)
  const [reviewError, setReviewError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      setTasks(await api.get('/api/admin/tasks'))
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { load() }, [load])

  function openReview(task) {
    setStatus(task.AdminStatus === 'Pending' ? 'Approved' : task.AdminStatus)
    setRemarks(task.AdminRemarks || '')
    setReviewError('')
    setReviewing(task)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setReviewError('')
    try {
      await api.patch(`/api/admin/tasks/${reviewing.ID}/review`, { admin_status: status, admin_remarks: remarks })
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
      <div className="page-header"><h1>Task Review</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="table-wrap">
          {tasks.length ? (
            <table>
              <thead><tr><th>Employee</th><th>Client</th><th>Project</th><th>Date</th><th>Priority</th><th>Review status</th><th></th></tr></thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.ID}>
                    <td>{t.EmployeeName}</td>
                    <td>{t.ClientName}</td>
                    <td>{t.ProjectName}</td>
<<<<<<< HEAD
                    <td>{fmtDate(t.TaskDate)}</td>
=======
                    <td>{t.TaskDate}</td>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
                    <td>{t.Priority}</td>
                    <td><StatusPill status={t.AdminStatus} /></td>
                    <td><button className="btn btn-secondary btn-sm" onClick={() => openReview(t)}>Review</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No tasks submitted yet.</div>
          )}
        </div>
      </div>

      {reviewing && (
        <Modal title={`Review: ${reviewing.ProjectName}`} onClose={() => setReviewing(null)}>
          {reviewError && <div className="banner banner-error">{reviewError}</div>}
          <p style={{ fontSize: 14 }}>{reviewing.Description}</p>
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Decision</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                {ADMIN_STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
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
