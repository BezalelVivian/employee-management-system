import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { fmtDate, dmyToIso } from '../utils/time'

// Drop-in replacement for <input type="date">: shows/accepts DD-MM-YYYY everywhere, and still
// gives a calendar popup. `value` and onChange's e.target.value are ISO (YYYY-MM-DD) like before.
export default function DateInput({ value, onChange, min, max, required, id, disabled, className = '' }) {
  const [text, setText] = useState(value ? fmtDate(value) : '')
  const nativeRef = useRef(null)

  // Follow outside changes (form reset, picker), but don't fight the user mid-typing.
  useEffect(() => {
    if (value !== dmyToIso(text)) setText(value ? fmtDate(value) : '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  function handleText(e) {
    let digits = e.target.value.replace(/\D/g, '').slice(0, 8)
    let out = digits
    if (digits.length > 4) out = `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`
    else if (digits.length > 2) out = `${digits.slice(0, 2)}-${digits.slice(2)}`
    setText(out)
    const iso = dmyToIso(out)
    const bad = iso && ((min && iso < min) || (max && iso > max))
    e.target.setCustomValidity(bad ? 'Date is outside the allowed range' : '')
    onChange({ target: { value: bad ? '' : iso } })
  }

  function openPicker() {
    try { nativeRef.current?.showPicker() } catch { nativeRef.current?.focus() }
  }

  return (
    <div className={`date-input ${className}`.trim()}>
      <input
        id={id} type="text" inputMode="numeric" placeholder="DD-MM-YYYY" maxLength={10}
        autoComplete="off" value={text} onChange={handleText} required={required} disabled={disabled}
        pattern="\d{2}-\d{2}-\d{4}" title="Use DD-MM-YYYY"
      />
      <button type="button" className="date-input-btn" onClick={openPicker} disabled={disabled} aria-label="Open calendar">
        <Icon name="calendar" size={17} />
      </button>
      <input
        ref={nativeRef} type="date" className="date-native" tabIndex={-1} aria-hidden="true"
        value={value || ''} min={min} max={max} disabled={disabled}
        onChange={(e) => { if (e.target.value) onChange({ target: { value: e.target.value } }) }}
      />
    </div>
  )
}
