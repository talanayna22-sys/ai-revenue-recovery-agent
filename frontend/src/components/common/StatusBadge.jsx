const STATUS_STYLES = {
  DETECTED:   { color: 'var(--info)',   bg: 'var(--info-soft)' },
  ANALYZING:  { color: 'var(--info)',   bg: 'var(--info-soft)' },
  ACTION_TAKEN: { color: 'var(--info)', bg: 'var(--info-soft)' },
  PENDING_RETRY: { color: 'var(--warn)', bg: 'var(--warn-soft)' },
  RECOVERED:  { color: 'var(--accent)', bg: 'var(--accent-soft)' },
  FAILED:     { color: 'var(--risk)',   bg: 'var(--risk-soft)' },
  ESCALATED:  { color: 'var(--risk)',   bg: 'var(--risk-soft)' },
  STOPPED:    { color: 'var(--text-muted)', bg: 'var(--border-soft)' },
  success:    { color: 'var(--accent)', bg: 'var(--accent-soft)' },
  failed:     { color: 'var(--risk)',   bg: 'var(--risk-soft)' },
  pending:    { color: 'var(--warn)',   bg: 'var(--warn-soft)' },
}

const LABELS = {
  DETECTED: 'Detected',
  ANALYZING: 'Analyzing',
  ACTION_TAKEN: 'Action taken',
  PENDING_RETRY: 'Pending retry',
  RECOVERED: 'Recovered',
  FAILED: 'Failed',
  ESCALATED: 'Escalated',
  STOPPED: 'Stopped',
}

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || { color: 'var(--text-muted)', bg: 'var(--border-soft)' }
  const label = LABELS[status] || status
  return (
    <span className="badge" style={{ color: style.color, background: style.bg }}>
      <span className="badge-dot" style={{ background: style.color }} />
      {label}
    </span>
  )
}
