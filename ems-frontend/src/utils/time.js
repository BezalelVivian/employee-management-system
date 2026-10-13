// The API always returns local company time as "YYYY-MM-DDTHH:MM:SS" (no timezone).
// We parse that with a regex instead of `new Date(...)`, so a bad/odd value shows a dash
// instead of "Invalid Date", and the browser's own timezone can never shift the time.
const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/

export function fmtTime(iso) {
  const m = ISO_RE.exec(iso || '')
  if (!m) return '—'
  const h = Number(m[4])
  const suffix = h >= 12 ? 'PM' : 'AM'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}:${m[5]} ${suffix}`
}

export function fmtTimeInput(iso) {
  // "HH:MM" for <input type="time">
  const m = ISO_RE.exec(iso || '')
  return m ? `${m[4]}:${m[5]}` : ''
}

// Every date in the app is shown as DD-MM-YYYY (stored/sent as YYYY-MM-DD).
export function fmtDate(isoDate) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate || '')
  return m ? `${m[3]}-${m[2]}-${m[1]}` : '—'
}

// "05-10-2026" -> "2026-10-05" (or '' if it is not a real calendar date)
export function dmyToIso(text) {
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(text || '')
  if (!m) return ''
  const [d, mo, y] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const dt = new Date(y, mo - 1, d)
  if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) return ''
  return `${m[3]}-${m[2]}-${m[1]}`
}

export function fmtDateTime(iso) {
  return ISO_RE.test(iso || '') ? `${fmtDate(iso)}, ${fmtTime(iso)}` : ''
}

export function todayLocalISO() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
