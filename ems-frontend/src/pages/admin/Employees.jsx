import { useEffect, useState, useCallback } from 'react'
import DateInput from '../../components/DateInput'
import { todayLocalISO } from '../../utils/time'
import { api } from '../../api/client'
import StatusPill from '../../components/StatusPill'
import Modal from '../../components/Modal'
import Avatar from '../../components/Avatar'
import PhotoPicker from '../../components/PhotoPicker'
import { useConfirm } from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'

const emptyCreateForm = {
  name: '', email: '', phone: '', dob: '', designation: '', departmentId: '',
  roleTitle: '', address: '', joinedDate: todayLocalISO(), tempPassword: '',
}

// Department dropdown fed by the Departments sheet. If the sheet has no departments yet (or an
// employee still has an old value that isn't in it), it falls back gracefully instead of blocking.
function DepartmentSelect({ departments, value, onChange }) {
  const known = departments.some((d) => String(d.ID) === String(value))
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
      <option value="">— None —</option>
      {value && !known && <option value={value}>{value} (not in Departments list)</option>}
      {departments.map((d) => <option key={d.ID} value={d.ID}>{d.Name}</option>)}
    </select>
  )
}

export default function Employees() {
  const confirm = useConfirm()
  const toast = useToast()
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
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
  const [photos, setPhotos] = useState({})
  const [photoFor, setPhotoFor] = useState(null)

  const load = useCallback(async () => {
    try {
      setError('')
      const res = await api.get('/api/admin/employees')
      setEmployees(res)
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { load() }, [load])
  // One request for every photo; purely cosmetic, so a failure just shows initials.
  useEffect(() => {
    api.get('/api/admin/photos').then((p) => setPhotos(p || {})).catch(() => setPhotos({}))
  }, [])
  useEffect(() => {
    api.get('/api/admin/departments').then(setDepartments).catch(() => setDepartments([]))
  }, [])

  function isActive(e) {
    return String(e.IsActive).toUpperCase() === 'TRUE' || e.IsActive === true
  }

  async function handleToggle(emp) {
    const deactivating = isActive(emp)
    const ok = await confirm({
      title: deactivating ? `Deactivate ${emp.Name}?` : `Activate ${emp.Name}?`,
      message: deactivating ? 'They will not be able to log in until you activate them again.' : 'They will be able to log in again.',
      confirmText: deactivating ? 'Yes, deactivate' : 'Yes, activate',
      danger: deactivating,
    })
    if (!ok) return
    try {
      await api.patch(`/api/admin/employees/${emp.ID}/toggle-active`)
      toast(deactivating ? `${emp.Name} deactivated` : `${emp.Name} activated`)
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
    const ok = await confirm({
      title: `Reset password for ${resetting.Name}?`,
      message: 'Their current password will stop working immediately.',
      confirmText: 'Yes, reset password',
      danger: true,
    })
    if (!ok) return
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
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Avatar name={e.Name} src={photos[e.ID]} size="sm" />
                        <span>{e.Name}</span>
                      </div>
                    </td>
                    <td>{e.Email}</td>
                    <td>{e.Designation}</td>
                    <td>{e.DepartmentName || e.DepartmentID}</td>
                    <td><StatusPill status={isActive(e) ? 'Present' : 'Absent'} />
                      <span style={{ marginLeft: 6, fontSize: 12.5, color: 'var(--muted)' }}>{isActive(e) ? 'Active' : 'Inactive'}</span>
                    </td>
                    <td className="row-actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(e)}>Edit</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => setPhotoFor(e)}>Photo</button>
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
              <div className="field"><label>DOB</label><DateInput value={createForm.dob} onChange={(e) => setCreateForm({ ...createForm, dob: e.target.value })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Designation</label><input value={createForm.designation} onChange={(e) => setCreateForm({ ...createForm, designation: e.target.value })} /></div>
              <div className="field"><label>Department</label><DepartmentSelect departments={departments} value={createForm.departmentId} onChange={(v) => setCreateForm({ ...createForm, departmentId: v })} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Role title</label><input value={createForm.roleTitle} onChange={(e) => setCreateForm({ ...createForm, roleTitle: e.target.value })} /></div>
              <div className="field"><label>Joined date</label><DateInput required value={createForm.joinedDate} onChange={(e) => setCreateForm({ ...createForm, joinedDate: e.target.value })} /></div>
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
              <div className="field"><label>Department</label><DepartmentSelect departments={departments} value={editForm.departmentId} onChange={(v) => setEditForm({ ...editForm, departmentId: v })} /></div>
              <div className="field"><label>Role title</label><input value={editForm.roleTitle} onChange={(e) => setEditForm({ ...editForm, roleTitle: e.target.value })} /></div>
            </div>
            <div className="field"><label>Joined date</label><DateInput value={editForm.joinedDate} onChange={(e) => setEditForm({ ...editForm, joinedDate: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          </form>
        </Modal>
      )}

      {photoFor && (
        <Modal title={`Photo — ${photoFor.Name}`} onClose={() => setPhotoFor(null)}>
          <PhotoPicker
            name={photoFor.Name}
            photo={photos[photoFor.ID]}
            onUpload={async (dataUrl) => {
              await api.put(`/api/admin/employees/${photoFor.ID}/photo`, { photo: dataUrl })
              setPhotos((prev) => ({ ...prev, [photoFor.ID]: dataUrl }))
            }}
            onRemove={async () => {
              await api.del(`/api/admin/employees/${photoFor.ID}/photo`)
              setPhotos((prev) => { const next = { ...prev }; delete next[photoFor.ID]; return next })
            }}
          />
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