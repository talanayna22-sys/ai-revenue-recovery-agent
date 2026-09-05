import { useEffect, useState } from 'react'
import { X, Sparkles, ShieldCheck, ArrowRight } from 'lucide-react'
import { api } from '../../api/client.js'
import StatusBadge from '../common/StatusBadge.jsx'
import { LoadingSpinner } from '../common/EmptyState.jsx'
import { fmtINR, fmtTime, ACTION_LABELS } from './CaseTable.jsx'

export default function CaseDetailDrawer({ caseId, onClose, onChanged }) {
  const [caseData, setCaseData] = useState(null)
  const [actions, setActions] = useState([])
  const [audit, setAudit] = useState([])
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([api.getCase(caseId), api.getCaseActions(caseId), api.getCaseAudit(caseId)])
      .then(([c, a, l]) => {
        setCaseData(c.data)
        setActions(a.data)
        setAudit(l.data)
        setError(null)
      })
      .catch((e) => setError(e?.response?.data?.error || 'Failed to load case.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [caseId])

  const handleExecute = async () => {
    setConfirmOpen(false)
    setExecuting(true)
    try {
      await api.executeRecovery(caseId)
      load()
      onChanged?.()
    } catch (e) {
      setError(e?.response?.data?.error || 'Recovery execution failed.')
    } finally {
      setExecuting(false)
    }
  }

  const isTerminal = caseData && ['RECOVERED', 'ESCALATED', 'STOPPED'].includes(caseData.status)
  const latestAction = actions[actions.length - 1]

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18 }}>Case #{caseId}</h2>
            {caseData && <div className="page-subtitle">{caseData.customer_name} · {caseData.customer_email}</div>}
          </div>
          <button onClick={onClose} className="btn" style={{ padding: 8 }}><X size={16} /></button>
        </div>

        {loading && <LoadingSpinner label="Loading case…" />}
        {error && <div style={{ color: 'var(--risk)', fontSize: 13, marginBottom: 16 }}>{error}</div>}

        {caseData && !loading && (
          <>
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>Revenue at risk</span>
                <StatusBadge status={caseData.status} />
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700 }}>
                {fmtINR(caseData.amount_at_risk)}
              </div>
              {caseData.recovered_amount > 0 && (
                <div style={{ color: 'var(--accent)', fontSize: 13, marginTop: 6 }}>
                  {fmtINR(caseData.recovered_amount)} recovered
                </div>
              )}
              <div style={{ display: 'flex', gap: 16, marginTop: 14, fontSize: 12.5, color: 'var(--text-muted)' }}>
                <span>Retries: {caseData.retry_count}/{caseData.max_retries}</span>
                <span>Notifications: {caseData.notification_count}</span>
              </div>
            </div>

            {latestAction && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <Sparkles size={15} color="var(--info)" />
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>AI recommendation vs. final decision</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.6 }}>
                  {latestAction.ai_reasoning}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <span style={{
                    padding: '4px 10px', borderRadius: 6, background: 'var(--info-soft)', color: 'var(--info)',
                  }}>
                    {ACTION_LABELS[latestAction.ai_recommended_action] || latestAction.ai_recommended_action}
                  </span>
                  <ArrowRight size={14} color="var(--text-faint)" />
                  <span style={{
                    padding: '4px 10px', borderRadius: 6,
                    background: latestAction.guardrail_overridden ? 'var(--warn-soft)' : 'var(--accent-soft)',
                    color: latestAction.guardrail_overridden ? 'var(--warn)' : 'var(--accent)',
                  }}>
                    {ACTION_LABELS[latestAction.final_action] || latestAction.final_action}
                  </span>
                  {latestAction.guardrail_overridden ? (
                    <span style={{ fontSize: 11.5, color: 'var(--warn)' }}>overridden</span>
                  ) : null}
                </div>
                {latestAction.guardrail_overridden && (
                  <div style={{
                    display: 'flex', gap: 8, marginTop: 12, padding: 10, borderRadius: 8,
                    background: 'var(--warn-soft)', fontSize: 12.5, color: 'var(--text)',
                  }}>
                    <ShieldCheck size={15} color="var(--warn)" style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>{latestAction.guardrail_note}</span>
                  </div>
                )}
                <div style={{ fontSize: 11.5, color: 'var(--text-faint)', marginTop: 10 }}>
                  Confidence {(latestAction.ai_confidence * 100).toFixed(0)}% · source: {latestAction.ai_source}
                </div>
              </div>
            )}

            <div style={{ marginBottom: 20 }}>
              {!isTerminal ? (
                <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
                        onClick={() => setConfirmOpen(true)} disabled={executing}>
                  {executing ? 'Running recovery…' : 'Execute recovery'}
                </button>
              ) : (
                <div className="btn" style={{ width: '100%', justifyContent: 'center', opacity: 0.7 }}>
                  Case is {caseData.status.toLowerCase()} — no further action available
                </div>
              )}
            </div>

            {confirmOpen && (
              <div className="card" style={{ marginBottom: 20, borderColor: 'var(--warn)' }}>
                <p style={{ margin: '0 0 12px', fontSize: 13 }}>
                  This runs one pass of the recovery agent (analyze → decide → guardrail check → act) for this case. Continue?
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={handleExecute}>Confirm</button>
                  <button className="btn" onClick={() => setConfirmOpen(false)}>Cancel</button>
                </div>
              </div>
            )}

            <h3 style={{ fontSize: 13.5, marginBottom: 12, color: 'var(--text-muted)' }}>Timeline</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {audit.map((entry, i) => (
                <div key={entry.id} style={{ display: 'flex', gap: 12, paddingBottom: 16, position: 'relative' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0, marginTop: 4,
                    }} />
                    {i < audit.length - 1 && <div style={{ width: 1, flex: 1, background: 'var(--border-soft)' }} />}
                  </div>
                  <div style={{ paddingBottom: 4 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 500 }}>{entry.event}</div>
                    {entry.detail && (
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.5 }}>
                        {entry.detail}
                      </div>
                    )}
                    <div style={{ fontSize: 11, color: 'var(--text-faint)', marginTop: 3 }}>
                      {fmtTime(entry.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}
