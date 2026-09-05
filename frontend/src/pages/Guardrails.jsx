import { useEffect, useState } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'
import { api } from '../api/client.js'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'

export default function Guardrails() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    api.guardrails()
      .then((r) => { setData(r.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not load guardrail configuration.'))
  }

  useEffect(() => { load() }, [])

  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return <LoadingSpinner label="Loading guardrails…" />

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Guardrails</h1>
          <div className="page-subtitle">Deterministic safety rules. The AI advises; these rules have final authority.</div>
        </div>
      </div>

      {data.recovery_kill_switch && (
        <div className="card" style={{ marginBottom: 20, borderColor: 'var(--risk)', display: 'flex', gap: 10 }}>
          <AlertTriangle size={18} color="var(--risk)" style={{ flexShrink: 0 }} />
          <div>
            <strong style={{ color: 'var(--risk)' }}>Kill switch is ENABLED</strong>
            <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 2 }}>
              All automated recovery actions are currently paused; every case is routed to escalation.
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
        <ConfigTile label="Max retries" value={data.max_retries} />
        <ConfigTile label="Retry cooldown" value={`${data.retry_cooldown_minutes} min`} />
        <ConfigTile label="High-value threshold" value={`₹${Number(data.high_value_threshold).toLocaleString('en-IN')}`} />
        <ConfigTile label="Max notifications / customer" value={data.max_notifications} />
        <ConfigTile label="Active payment mode" value={data.payment_mode === 'razorpay_test' ? 'Razorpay Test Mode' : 'Synthetic Mode'} />
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, marginBottom: 14 }}>Allowed actions by scenario</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {Object.entries(data.allowed_actions).map(([scenario, actions]) => (
            <div key={scenario}>
              <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'capitalize' }}>
                {scenario.replaceAll('_', ' ')}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {actions.map((a) => (
                  <span key={a} style={{
                    fontSize: 12, padding: '4px 10px', borderRadius: 6,
                    background: 'var(--surface-raised)', border: '1px solid var(--border-soft)',
                  }}>
                    {a.replaceAll('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 14, marginBottom: 14 }}>Stopping rules</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.rules.map((rule, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, fontSize: 13, color: 'var(--text-muted)' }}>
              <ShieldCheck size={16} color="var(--accent)" style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{rule}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

function ConfigTile({ label, value }) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 180 }}>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700 }}>{value}</div>
    </div>
  )
}
