export function initials(name) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
}

// Same name -> same colour everywhere (6 tonal colours, see .avatar-t0 … .avatar-t5 in the CSS).
function tone(name) {
  let h = 0
  for (const ch of (name || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return h % 6
}

// Round avatar: the employee's photo if they have one, otherwise their initials.
// `size` is one of '', 'sm', 'lg' (matches the .avatar-sm / .avatar-lg CSS classes).
export default function Avatar({ name, src, size = '' }) {
  const cls = `avatar ${size ? `avatar-${size}` : ''}`.trim()
  if (src) return <img className={`${cls} avatar-img`} src={src} alt="" />
  return <div className={`${cls} avatar-t${tone(name)}`} aria-hidden="true">{initials(name)}</div>
}