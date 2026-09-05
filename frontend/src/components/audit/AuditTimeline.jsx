import { fmtTime } from '../cases/CaseTable.jsx'
import { EmptyState } from '../common/EmptyState.jsx'

export default function AuditTimeline({ logs }) {
  if (!logs || logs.length === 0) {
    return <EmptyState title="No audit events yet" description="Run batch recovery or execute a case to generate audit trail entries." />
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Case</th>
            <th>Event</th>
            <th>Actor</th>
            <th>Detail</th>
            <th>Amount</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id} style={{ cursor: 'default' }}>
              <td style={{ color: 'var(--text-muted)' }}>{fmtTime(l.created_at)}</td>
              <td className="mono">{l.recovery_case_id ? `#${l.recovery_case_id}` : '—'}</td>
              <td>{l.event}</td>
              <td style={{ textTransform: 'capitalize' }}>{l.actor}</td>
              <td style={{ color: 'var(--text-muted)', whiteSpace: 'normal', minWidth: 260 }}>{l.detail}</td>
              <td>{l.amount ? `₹${Number(l.amount).toLocaleString('en-IN')}` : '—'}</td>
              <td style={{ color: 'var(--text-muted)' }}>{l.status_at_event || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
