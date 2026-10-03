import { useEffect, useState, useCallback } from 'react'
<<<<<<< HEAD
import DateInput from '../../components/DateInput'
import { todayLocalISO, fmtDate } from '../../utils/time'
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
import { useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'

const STATUS_OPTIONS = ['Pending', 'In Progress', 'Completed']
const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Urgent']

const emptyForm = {
  clientName: '', projectName: '', description: '', status: 'Pending',
<<<<<<< HEAD
  priority: 'Medium', remarks: '', taskDate: todayLocalISO(),
=======
  priority: 'Medium', remarks: '', taskDate: new Date().toISOString().slice(0, 10),
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
}

export default function Tasks() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tasks, setTasks] = useState([])
  const [summary, setSummary] = useState(null)
  const [filters, setFilters] = useState({ search: '', status: '', priority: '' })
  const [editing, setEditing] = useState(null) // null = closed, {} = new, {...task} = editing
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setError('')
      const [list, sum] = await Promise.all([
        api.get('/api/employee/tasks', filters),
        api.get('/api/employee/tasks/summary'),
      ])
      setTasks(list)
      setSummary(sum)
    } catch (err) { setError(err.message) }
  }, [filters])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      openNew()
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function openNew() {
    setForm(emptyForm)
    setFormError('')
    setEditing({})
  }

  function openEdit(task) {
    setForm({
      clientName: task.clientName, projectName: task.projectName, description: task.description,
      status: task.status, priority: task.priority, remarks: task.remarks, taskDate: task.taskDate,
    })
    setFormError('')
    setEditing(task)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    const body = {
      client_name: form.clientName, project_name: form.projectName, description: form.description,
      status: form.status, priority: form.priority, remarks: form.remarks, task_date: form.taskDate,
    }
    try {
      if (editing?.id) {
        await api.put(`/api/employee/tasks/${editing.id}`, body)
      } else {
        await api.post('/api/employee/tasks', body)
      }
      setEditing(null)
      await load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header"><h1>Tasks</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      {summary && (
        <div className="grid-3">
          <div className="stat"><div className="value">{summary.completed}</div><div className="label">Completed</div></div>
          <div className="stat"><div className="value">{summary.inProgress}</div><div className="label">In Progress</div></div>
          <div className="stat"><div className="value">{summary.pending}</div><div className="label">Pending</div></div>
        </div>
      )}

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="toolbar">
          <input
            className="search-input" placeholder="Search client, project, or description…"
            value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
            <option value="">All priorities</option>
            {PRIORITY_OPTIONS.map((p) => <option key={p}>{p}</option>)}
          </select>
          <button className="btn btn-primary" onClick={openNew}>Submit Task</button>
        </div>

        <div className="table-wrap">
          {tasks.length ? (
            <table>
              <thead>
                <tr><th>Client</th><th>Project</th><th>Date</th><th>Status</th><th>Priority</th><th>Admin review</th><th></th></tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td>{t.clientName}</td>
                    <td>{t.projectName}</td>
<<<<<<< HEAD
                    <td>{fmtDate(t.taskDate)}</td>
=======
                    <td>{t.taskDate}</td>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
                    <td><StatusPill status={t.status} /></td>
                    <td>{t.priority}</td>
                    <td><StatusPill status={t.adminStatus} /></td>
                    <td><button className="btn btn-secondary btn-sm" onClick={() => openEdit(t)}>Edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No tasks match these filters yet.</div>
          )}
        </div>
      </div>

      {editing !== null && (
        <Modal title={editing.id ? 'Edit task' : 'Submit task'} onClose={() => setEditing(null)}>
          {formError && <div className="banner banner-error">{formError}</div>}
          <form onSubmit={handleSubmit}>
            <div className="field-row">
              <div className="field">
                <label>Client name</label>
                <input required value={form.clientName} onChange={(e) => setForm({ ...form, clientName: e.target.value })} />
              </div>
              <div className="field">
                <label>Project name</label>
                <input required value={form.projectName} onChange={(e) => setForm({ ...form, projectName: e.target.value })} />
              </div>
            </div>
            <div className="field">
              <label>Description</label>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Status</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Priority</label>
                <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                  {PRIORITY_OPTIONS.map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Date</label>
<<<<<<< HEAD
                <DateInput required value={form.taskDate} onChange={(e) => setForm({ ...form, taskDate: e.target.value })} />
=======
                <input type="date" required value={form.taskDate} onChange={(e) => setForm({ ...form, taskDate: e.target.value })} />
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
              </div>
            </div>
            <div className="field">
              <label>Remarks</label>
              <textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} />
            </div>
            {editing.id && <p className="hint-text">Saving will send this task back to Pending for admin re-review.</p>}
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </form>
        </Modal>
      )}
    </div>
  )
}
