const TONE_MAP = {
  // attendance (Attendance History also returns these three, from /api/employee/attendance)
  Present: 'green', Late: 'amber', Absent: 'red',
  'Half Day': 'amber', 'Short Hours': 'amber', 'Missing Check-out': 'amber', 'Not checked in': 'muted',
  'On Leave': 'green', Holiday: 'muted', 'Weekly Off': 'muted',
  // before the person could use EMS (join date / go-live): neutral, deliberately NOT red like Absent
  'Not Tracked': 'muted', 'Not joined yet': 'muted',
  // employee accounts
  Active: 'green', Inactive: 'muted',
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