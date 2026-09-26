import { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'

const emptyCreateForm = {
  name: '', email: '', phone: '', dob: '', designation: '', departmentId: '',
  roleTitle: '', address: '', joinedDate: new Date().toISOString().slice(0, 10), tempPassword: '',
}

export default function Employees() {
  const [employees, setEmployees] = useState([])
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState(emptyCreateForm)
  const [createError, setCreateError] = useState('')
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [editError, setEditError] = useState('')
  const [resetting, setResetting] = useState(null)
  const [resetPassword, setResetPassword] = useState('')
  const [resetError, setResetError] = useState('')
  const [resetMessage, setResetMessage] = useState('')
  const [resetSaving, setResetSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/admin/employees')
      setEmployees(res)
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { load() }, [load])

  function isActive(e) {
    return String(e.IsActive).toUpperCase() === 'TRUE' || e.IsActive === true
  }

  async function handleToggle(emp) {
    try {
      await api.patch(`/api/admin/employees/${emp.ID}/toggle-active`)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    setCreateError('')
    try {
      await api.post('/api/admin/employees', {
        name: createForm.name, email: createForm.email, phone: createForm.phone,
        dob: createForm.dob || null, designation: createForm.designation,
        department_id: createForm.departmentId, role_title: createForm.roleTitle,
        address: createForm.address, joined_date: createForm.joinedDate,
        temp_password: createForm.tempPassword,
      })
      setShowCreate(false)
      setCreateForm(emptyCreateForm)
      await load()
    } catch (err) {
      setCreateError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function openEdit(emp) {
    setEditForm({
      employeeCode: emp.EmployeeCode, name: emp.Name, email: emp.Email,
      designation: emp.Designation, departmentId: emp.DepartmentID,
      roleTitle: emp.RoleTitle, joinedDate: emp.JoinedDate,
    })
    setEditError('')
    setEditing(emp)
  }

  async function handleEditSave(e) {
    e.preventDefault()
    setSaving(true)
    setEditError('')
    try {
      await api.patch(`/api/admin/employees/${editing.ID}`, {
        employee_code: editForm.employeeCode, name: editForm.name, email: editForm.email,
        designation: editForm.designation, department_id: editForm.departmentId,
        role_title: editForm.roleTitle, joined_date: editForm.joinedDate,
      })
      setEditing(null)
      await load()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function openReset(emp) {
    setResetPassword('')
    setResetError('')
    setResetMessage('')
    setResetting(emp)
  }

  async function handleResetSave(e) {
    e.preventDefault()
    if (resetPassword.length < 6) {
      setResetError('Temporary password must be at least 6 characters.')
      return
    }
    setResetSaving(true)
    setResetError('')
    setResetMessage('')
    try {
      await api.post(`/api/admin/employees/${resetting.ID}/reset-password`, { new_temp_password: resetPassword })
      setResetMessage(`Password reset. Share this temporary password with ${resetting.Name} directly: "${resetPassword}"`)
    } catch (err) {
      setResetError(err.message)
    } finally {
      setResetSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header"><h1>Employees</h1></div>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <div style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={() => { setCreateForm(emptyCreateForm); setCreateError(''); setShowCreate(true) }}>Add Employee</button>
        </div>
        <div className="table-wrap">
          {employees.length ? (
            <table>
              <thead><tr><th>Code</th><th>Name</th><th>Email</th><th>Designation</th><th>Department</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {employees.map((e) => (
                  <tr key={e.ID}>
                    <td>{e.EmployeeCode}</td>
                    <td>{e.Name}</td>
                    <td>{e.Email}</td>
                    <td>{e.Designation}</td>
                    <td>{e.DepartmentID}</td>
                    <td><StatusPill status={isActive(e) ? 'Present' : 'Absent'} />
                      <span style={{ marginLeft: 6, fontSize: 12.5, color: 'var(--muted)' }}>{isActive(e) ? 'Active' : 'Inactive'}</span>
                    </td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(e)}>Edit</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => openReset(e)}>Reset Password</button>
                      <button className={`btn btn-sm ${isActive(e) ? 'btn-danger' : 'btn-secondary'}`} onClick={() => handleToggle(e)}>
                        {isActive(e) ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="table-empty">No employees yet — add the first one.</div>
          )}
        </div>
      </div>

      {showCreate && (
        <Modal title="Add employee" onClose={() => setShowCreate(false)}>
          {createError && <div className="banner banner-error">{createError}</div>}
          <form onSubmit={handleCreate}>
            <div className="field-row">
              <div className="field"><label>Name</label><input required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} /></div>
              <div className="field"><label>Email</label><input type="email" required value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Phone</label><input value={createForm.phone} maxLength={10} inputMode="numeric" placeholder="10-digit mobile number" onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value.replace(/\D/g, '') })} /></div>
              <div className="field"><label>DOB</label><input type="date" value={createForm.dob} onChange={(e) => setCreateForm({ ...createForm, dob: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Designation</label><input value={createForm.designation} onChange={(e) => setCreateForm({ ...createForm, designation: e.target.value })} /></div>
              <div className="field"><label>Department ID</label><input value={createForm.departmentId} onChange={(e) => setCreateForm({ ...createForm, departmentId: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Role title</label><input value={createForm.roleTitle} onChange={(e) => setCreateForm({ ...createForm, roleTitle: e.target.value })} /></div>
              <div className="field"><label>Joined date</label><input type="date" required value={createForm.joinedDate} onChange={(e) => setCreateForm({ ...createForm, joinedDate: e.target.value })} /></div>
            </div>
            <div className="field"><label>Address</label><textarea value={createForm.address} onChange={(e) => setCreateForm({ ...createForm, address: e.target.value })} /></div>
            <div className="field">
              <label>Temporary password</label>
              <input required minLength={6} value={createForm.tempPassword} onChange={(e) => setCreateForm({ ...createForm, tempPassword: e.target.value })} />
              <p className="hint-text">Share this with the employee directly — there's no self-service password reset in this app.</p>
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create employee'}</button>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.Name}`} onClose={() => setEditing(null)}>
          {editError && <div className="banner banner-error">{editError}</div>}
          <form onSubmit={handleEditSave}>
            <div className="field-row">
              <div className="field"><label>Employee code</label><input value={editForm.employeeCode} onChange={(e) => setEditForm({ ...editForm, employeeCode: e.target.value })} /></div>
              <div className="field"><label>Name</label><input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Email</label><input type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} /></div>
              <div className="field"><label>Designation</label><input value={editForm.designation} onChange={(e) => setEditForm({ ...editForm, designation: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Department ID</label><input value={editForm.departmentId} onChange={(e) => setEditForm({ ...editForm, departmentId: e.target.value })} /></div>
              <div className="field"><label>Role title</label><input value={editForm.roleTitle} onChange={(e) => setEditForm({ ...editForm, roleTitle: e.target.value })} /></div>
            </div>
            <div className="field"><label>Joined date</label><input type="date" value={editForm.joinedDate} onChange={(e) => setEditForm({ ...editForm, joinedDate: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          </form>
        </Modal>
      )}

      {resetting && (
        <Modal title={`Reset password — ${resetting.Name}`} onClose={() => setResetting(null)}>
          {resetError && <div className="banner banner-error">{resetError}</div>}
          {resetMessage && <div className="banner banner-success">{resetMessage}</div>}
          {!resetMessage && (
            <form onSubmit={handleResetSave}>
              <p className="hint-text" style={{ marginTop: 0 }}>
                There's no self-service "forgot password" link yet — set a new temporary password here and share it with the employee directly. They can change it themselves afterward from their Profile page.
              </p>
              <div className="field">
                <label>New temporary password</label>
                <input required minLength={6} value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} />
              </div>
              <button className="btn btn-primary" type="submit" disabled={resetSaving}>{resetSaving ? 'Resetting…' : 'Reset password'}</button>
            </form>
          )}
        </Modal>
      )}
    </div>
  )
}