const TONE_MAP = {
  // attendance (Attendance History also returns these three, from /api/employee/attendance)
  Present: 'green', Late: 'amber', Absent: 'red',
  'Half Day': 'amber', 'Short Hours': 'amber', 'Missing Check-out': 'amber', 'Not checked in': 'muted',
  'On Leave': 'green', Holiday: 'muted', 'Weekly Off': 'muted',
  // tasks
  Completed: 'green', 'In Progress': 'amber', Pending: 'muted',
  // admin review / leave
  Approved: 'green', Rejected: 'red', 'Needs Changes': 'amber',
}

export default function StatusPill({ status }) {
  if (!status) return <span className="pill pill-muted">—</span>
  const tone = TONE_MAP[status] || 'muted'
  return <span className={`pill pill-${tone}`}>{status}</span>
}