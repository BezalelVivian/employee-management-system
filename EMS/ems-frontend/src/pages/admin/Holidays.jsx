import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import DateInput from '../../components/DateInput'
import Icon from '../../components/Icon'
import { useConfirm } from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { fmtDate, todayLocalISO } from '../../utils/time'

export default function Holidays() {
  const confirm = useConfirm()
  const toast = useToast()
  const [list, setList] = useState([])
  const [date, setDate] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const today = todayLocalISO()

  const load = useCallback(async () => {
    try { setError(''); setList(await api.get('/api/admin/holidays')) } catch (err) { setError(err.message) }
  }, [])
  useEffect(() => { load() }, [load])

  async function add(e) {
    e.preventDefault()
    if (!date) { setError('Pick a date in DD-MM-YYYY format.'); return }
    setSaving(true); setError('')
    try {
      await api.post('/api/admin/holidays', { date, name })
      setDate(''); setName(''); toast('Holiday added — employees will be notified 14 days before')
      await load()
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  async function remove(h) {
    if (!(await confirm({ title: 'Remove holiday?', message: `${h.name} (${fmtDate(h.date)}) will no longer be a holiday.`, confirmText: 'Remove', danger: true }))) return
    try { await api.del(`/api/admin/holidays/${h.id}`); toast('Holiday removed'); await load() } catch (err) { setError(err.message) }
  }

  const upcoming = list.filter((h) => h.date >= today)
  const past = list.filter((h) => h.date < today).reverse()

  return (
    <div>
      <div className="page-header"><h1>Holidays</h1><div className="clock">Employees get a bell notification and a dashboard card 14 days before each holiday.</div></div>
      {error && <div className="banner banner-error">{error}</div>}
      <div className="panel">
        <div className="panel-title"><h2>Add a holiday</h2></div>
        <form className="holiday-form" onSubmit={add}>
          <div className="field"><label>Date</label><DateInput required value={date} onChange={(e) => setDate(e.target.value)} /></div>
          <div className="field"><label>Name</label><input required value={name} maxLength={60} placeholder="e.g. Diwali" onChange={(e) => setName(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit" disabled={saving}><Icon name="plus" size={16} />{saving ? 'Adding…' : 'Add'}</button>
        </form>
      </div>
      <div className="panel">
        <div className="panel-title"><h2>Upcoming</h2></div>
        {upcoming.length ? (
          <ul className="holiday-list">
            {upcoming.map((h) => (
              <li key={h.id}><span className="holiday-date">{fmtDate(h.date)}</span><span className="holiday-name">{h.name}</span>
                <button className="btn btn-secondary btn-sm" onClick={() => remove(h)}><Icon name="trash" size={14} />Remove</button></li>
            ))}
          </ul>
        ) : <div className="empty-state"><Icon name="flag" size={28} /><div>No upcoming holidays yet.</div></div>}
        {past.length > 0 && <p className="hint-text">{past.length} past holiday{past.length > 1 ? 's' : ''} kept in the sheet.</p>}
      </div>
    </div>
  )
}
