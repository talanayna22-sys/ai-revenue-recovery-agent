import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client.js'
import DecisionFeed from '../components/agent/DecisionFeed.jsx'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'

const STEPS = ['Detect', 'Analyze', 'Decide', 'Guardrails', 'Act', 'Check result', 'Recover / Stop / Escalate']

const FILTERS = [
  { key: undefined, label: 'All' },
  { key: 'recovered', label: 'Recovered' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'pending', label: 'Pending' },
]

export default function AiAgent() {
  const [decisions, setDecisions] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState(undefined)

  const load = useCallback((outcome) => {
    api.aiDecisions(outcome ? { outcome } : {})
      .then((r) => { setDecisions(r.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not load AI agent decisions.'))
  }, [])

  useEffect(() => { load(filter) }, [filter, load])

  return (
    <>
      <div className="page-header">
        <div>
          <h1>AI Agent</h1>
          <div className="page-subtitle">Every recommendation the AI made, and what the guardrails actually approved.</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20, overflowX: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 0, minWidth: 620 }}>
          {STEPS.map((step, i) => (
            <div key={step} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, flex: 1 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'var(--surface-raised)', border: '1px solid var(--border)', fontSize: 12.5, fontWeight: 600,
                }}>
                  {i + 1}
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>{step}</span>
              </div>
              {i < STEPS.length - 1 && <div style={{ height: 1, flex: 0.6, background: 'var(--border)', marginBottom: 20 }} />}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {FILTERS.map((f) => (
          <button
            key={f.label}
            className="btn"
            style={{
              background: filter === f.key ? 'var(--accent-soft)' : undefined,
              borderColor: filter === f.key ? 'var(--accent)' : undefined,
              color: filter === f.key ? 'var(--accent)' : undefined,
            }}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && !decisions && <ErrorState message={error} onRetry={() => load(filter)} />}
      {!decisions && !error && <LoadingSpinner label="Loading AI decisions…" />}
      {decisions && decisions.length === 0 && (
        <div className="empty-state">
          <h3 style={{ color: 'var(--text)', fontSize: 15 }}>No decisions yet</h3>
          <p style={{ fontSize: 13 }}>Run batch recovery from the Dashboard to see the agent reason through cases.</p>
        </div>
      )}
      {decisions && decisions.length > 0 && <DecisionFeed decisions={decisions} />}
    </>
  )
}
