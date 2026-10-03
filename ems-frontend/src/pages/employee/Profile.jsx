import { useEffect, useState } from 'react'
import DateInput from '../../components/DateInput'
import { fmtDate } from '../../utils/time'
import { api, setToken } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import PhotoPicker from '../../components/PhotoPicker'

const READONLY_FIELDS = [
  ['EmployeeCode', 'Employee ID'],
  ['Name', 'Name'],
  ['Email', 'Email'],
  ['Designation', 'Designation'],
  ['DepartmentName', 'Department'],
  ['RoleTitle', 'Role'],
  ['JoinedDate', 'Joined'],
]

const emptyPasswordForm = { current_password: '', new_password: '', confirm_password: '' }

export default function Profile() {
  const { photo, setPhoto } = useAuth()
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({ phone: '', address: '', dob: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const [pwForm, setPwForm] = useState(emptyPasswordForm)
  const [pwError, setPwError] = useState('')
  const [pwMessage, setPwMessage] = useState('')
  const [pwSaving, setPwSaving] = useState(false)

  useEffect(() => {
    api.get('/api/employee/profile')
      .then((p) => {
        setProfile(p)
        setForm({ phone: p.Phone || '', address: p.Address || '', dob: p.DOB || '' })
      })
      .catch((err) => setError(err.message))
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      // The backend's dob field is Optional[date]: it accepts a real date or
      // null, but rejects an empty string as an invalid date. Coerce '' to
      // null so saving phone/address still works for anyone without a DOB
      // on file yet.
      await api.put('/api/employee/profile', { ...form, dob: form.dob || null })
      setMessage('Profile updated.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handlePasswordSave(e) {
    e.preventDefault()
    setPwError('')
    setPwMessage('')
    if (pwForm.new_password.length < 6) {
      setPwError('New password must be at least 6 characters.')
      return
    }
    if (pwForm.new_password !== pwForm.confirm_password) {
      setPwError('New password and confirmation do not match.')
      return
    }
    setPwSaving(true)
    try {
      const res = await api.put('/api/employee/password', {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      })
      // Only present if the backend session-invalidation feature is installed.
      if (res?.access_token) setToken(res.access_token)
      setPwMessage('Password updated.')
      setPwForm(emptyPasswordForm)
    } catch (err) {
      setPwError(err.message)
    } finally {
      setPwSaving(false)
    }
  }

  if (!profile && !error) {
    return (
      <div role="status" aria-live="polite">
        <span className="sr-only">Loading…</span>
        <div className="page-header"><h1>My Profile</h1></div>
        <div className="panel">
          <div className="skel skel-title" />
          <div className="photo-picker"><div className="skel" style={{ width: 96, height: 96, borderRadius: '50%', margin: 0 }} /><div className="skel" style={{ width: 220, height: 34, borderRadius: 99, margin: 0 }} /></div>
        </div>
        <div className="panel">
          <div className="skel skel-title" />
          <div className="grid-2">{Array.from({ length: 6 }, (_, i) => <div key={i} className="skel skel-field" />)}</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header"><h1>My Profile</h1></div>
      {error && <div className="banner banner-error">{error}</div>}
      {message && <div className="banner banner-success">{message}</div>}

      {profile && (
        <div className="panel">
          <div className="panel-title"><h2>Profile photo</h2></div>
          <PhotoPicker
            name={profile.Name}
            photo={photo}
            onUpload={async (dataUrl) => { await api.put('/api/employee/photo', { photo: dataUrl }); setPhoto(dataUrl) }}
            onRemove={async () => { await api.del('/api/employee/photo'); setPhoto(null) }}
          />
        </div>
      )}

      {profile && (
        <div className="panel">
          <div className="panel-title"><h2>Official record</h2></div>
          <p className="hint-text" style={{ marginTop: -8, marginBottom: 14 }}>These fields are admin-managed — contact your admin to change them.</p>
          <div className="grid-2">
            {READONLY_FIELDS.map(([key, label]) => (
              <div className="field" key={key}>
                <label>{label}</label>
                <input value={key === 'JoinedDate' ? (profile[key] ? fmtDate(profile[key]) : '') : (profile[key] || '')} disabled />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title"><h2>Editable details</h2></div>
        <form onSubmit={handleSave}>
          <div className="grid-2">
            <div className="field">
              <label htmlFor="phone">Phone</label>
              <input id="phone" value={form.phone} maxLength={10} inputMode="numeric" placeholder="10-digit mobile number" onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, '') })} />
            </div>
            <div className="field">
              <label htmlFor="dob">Date of birth</label>
              <DateInput id="dob" value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
            </div>
          </div>
          <div className="field">
            <label htmlFor="address">Address</label>
            <textarea id="address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
        </form>
      </div>

      <div className="panel">
        <div className="panel-title"><h2>Change password</h2></div>
        {pwError && <div className="banner banner-error">{pwError}</div>}
        {pwMessage && <div className="banner banner-success">{pwMessage}</div>}
        <form onSubmit={handlePasswordSave}>
          <div className="field">
            <label htmlFor="current_password">Current password</label>
            <input
              id="current_password" type="password" required autoComplete="current-password"
              value={pwForm.current_password}
              onChange={(e) => setPwForm({ ...pwForm, current_password: e.target.value })}
            />
          </div>
          <div className="grid-2">
            <div className="field">
              <label htmlFor="new_password">New password</label>
              <input
                id="new_password" type="password" required minLength={6} autoComplete="new-password"
                value={pwForm.new_password}
                onChange={(e) => setPwForm({ ...pwForm, new_password: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="confirm_password">Confirm new password</label>
              <input
                id="confirm_password" type="password" required minLength={6} autoComplete="new-password"
                value={pwForm.confirm_password}
                onChange={(e) => setPwForm({ ...pwForm, confirm_password: e.target.value })}
              />
            </div>
          </div>
          <p className="hint-text">At least 6 characters. You'll stay logged in on this device after changing it.</p>
          <button className="btn btn-primary" type="submit" disabled={pwSaving}>{pwSaving ? 'Updating…' : 'Update password'}</button>
        </form>
      </div>
    </div>
  )
}