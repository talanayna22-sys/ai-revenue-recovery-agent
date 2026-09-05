import StatusBadge from '../common/StatusBadge.jsx'
import { EmptyState } from '../common/EmptyState.jsx'

const fmtINR = (n) => '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })
const fmtTime = (t) => (t ? new Date(t.replace(' ', 'T')).toLocaleString('en-IN', {
  day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
}) : '—')

const ACTION_LABELS = {
  controlled_retry: 'Controlled retry',
  send_payment_link: 'Send payment link',
  notify_customer: 'Notify customer',
  wait: 'Wait',
  escalate: 'Escalate',
}

export default function CaseTable({ cases, columns, onRowClick, emptyTitle, emptyDescription }) {
  if (!cases || cases.length === 0) {
    return <EmptyState title={emptyTitle || 'No cases yet'} description={emptyDescription} />
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Case</th>
            <th>Customer</th>
            <th>Amount</th>
            {columns.map((c) => <th key={c.key}>{c.label}</th>)}
            <th>AI recommendation</th>
            <th>Final action</th>
            <th>Status</th>
            <th>Recovered</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id} onClick={() => onRowClick(c)}>
              <td className="mono">#{c.id}</td>
              <td>{c.customer_name}</td>
              <td>{fmtINR(c.amount_at_risk)}</td>
              {columns.map((col) => (
                <td key={col.key}>{col.render ? col.render(c) : (c.detail?.[col.key] ?? '—')}</td>
              ))}
              <td>{c.latest_ai_recommendation ? ACTION_LABELS[c.latest_ai_recommendation] : '—'}</td>
              <td>{c.latest_final_action ? ACTION_LABELS[c.latest_final_action] : '—'}</td>
              <td><StatusBadge status={c.status} /></td>
              <td>{c.recovered_amount > 0 ? fmtINR(c.recovered_amount) : '—'}</td>
              <td style={{ color: 'var(--text-muted)' }}>{fmtTime(c.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export { fmtINR, fmtTime, ACTION_LABELS }
