import { ArrowRight, ShieldCheck } from 'lucide-react'
import { fmtINR, fmtTime, ACTION_LABELS } from '../cases/CaseTable.jsx'
import StatusBadge from '../common/StatusBadge.jsx'

const SCENARIO_LABELS = {
  failed_payment: 'Failed Payment',
  checkout_dropoff: 'Checkout Drop-off',
  failed_subscription: 'Failed Subscription',
}

export default function DecisionFeed({ decisions }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {decisions.map((d) => (
        <div key={d.id} className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="mono" style={{ color: 'var(--text-faint)' }}>Case #{d.recovery_case_id}</span>
              <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{SCENARIO_LABELS[d.scenario_type]}</span>
              <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>· {d.customer_name}</span>
            </div>
            <StatusBadge status={d.case_status} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 14, marginBottom: 14 }}>
            <Field label="Input"><span>{fmtINR(d.amount_at_risk)} at risk</span></Field>
            <Field label="AI recommendation">
              <span style={{ color: 'var(--info)' }}>{ACTION_LABELS[d.ai_recommended_action] || d.ai_recommended_action}</span>
            </Field>
            <Field label="Confidence"><span>{(d.ai_confidence * 100).toFixed(0)}%</span></Field>
            <Field label="Final action">
              <span style={{ color: d.guardrail_overridden ? 'var(--warn)' : 'var(--accent)' }}>
                {ACTION_LABELS[d.final_action] || d.final_action}
              </span>
            </Field>
            <Field label="Result">
              <span style={{
                color: d.result === 'success' ? 'var(--accent)' : d.result === 'failed' ? 'var(--risk)' : 'var(--warn)',
              }}>
                {d.result}
              </span>
            </Field>
          </div>

          <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: d.guardrail_overridden ? 10 : 0 }}>
            <strong style={{ color: 'var(--text)' }}>Analysis: </strong>{d.ai_reasoning}
          </div>

          {d.guardrail_overridden === 1 && (
            <div style={{
              display: 'flex', gap: 8, padding: 10, borderRadius: 8, background: 'var(--warn-soft)', fontSize: 12.5,
            }}>
              <ShieldCheck size={15} color="var(--warn)" style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                <strong>Guardrail override:</strong> {d.guardrail_note}
              </span>
            </div>
          )}

          <div style={{ fontSize: 11.5, color: 'var(--text-faint)', marginTop: 10, display: 'flex', gap: 10, alignItems: 'center' }}>
            <span>{fmtTime(d.executed_at)}</span>
            <span>·</span>
            <span>source: {d.ai_source}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-faint)', marginBottom: 3, textTransform: 'none' }}>{label}</div>
      <div style={{ fontSize: 13 }}>{children}</div>
    </div>
  )
}
