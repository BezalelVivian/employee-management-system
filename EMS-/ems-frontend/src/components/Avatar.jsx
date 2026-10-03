export function initials(name) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
}

// Round avatar: the employee's photo if they have one, otherwise their initials.
// `size` is one of '', 'sm', 'lg' (matches the .avatar-sm / .avatar-lg CSS classes).
export default function Avatar({ name, src, size = '' }) {
  const cls = `avatar ${size ? `avatar-${size}` : ''}`.trim()
  if (src) return <img className={`${cls} avatar-img`} src={src} alt="" />
  return <div className={cls} aria-hidden="true">{initials(name)}</div>
}
