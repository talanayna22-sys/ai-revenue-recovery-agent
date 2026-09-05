import { useEffect, useState, useCallback } from 'react'
import { PlayCircle } from 'lucide-react'
import { api } from '../api/client.js'
import KpiCard from '../components/dashboard/KpiCard.jsx'
import { RecoveryByScenarioChart, CaseStatusChart } from '../components/dashboard/Charts.jsx'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'
import { fmtTime } from '../components/cases/CaseTable.jsx'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [charts, setCharts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const [batchResult, setBatchResult] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([api.dashboardSummary(), api.dashboardCharts()])
      .then(([s, c]) => { setSummary(s.data); setCharts(c.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not reach the backend API.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const handleRunBatch = async () => {
    setRunning(true)
    setBatchResult(null)
    try {
      const res = await api.runBatch()
      setBatchResult(res.data.summary)
      load()
    } catch (e) {
      setError(e?.response?.data?.error || 'Batch recovery failed to run.')
    } finally {
      setRunning(false)
    }
  }

  if (loading && !summary) return <LoadingSpinner label="Loading dashboard…" />
  if (error && !summary) return <ErrorState message={error} onRetry={load} />

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Revenue Recovery Dashboard</h1>
          <div className="page-subtitle">Live, computed from every case currently in the system — nothing here is hardcoded.</div>
        </div>
        <button className="btn btn-primary" onClick={handleRunBatch} disabled={running}>
          <PlayCircle size={16} />
          {running ? 'Running batch recovery…' : 'Run Batch Recovery'}
        </button>
      </div>

      {batchResult && (
        <div className="card" style={{ marginBottom: 20, display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13 }}>
          <span>Processed: <strong>{batchResult.processed}</strong></span>
          <span style={{ color: 'var(--accent)' }}>Recovered: <strong>{batchResult.recovered}</strong></span>
          <span style={{ color: 'var(--risk)' }}>Escalated: <strong>{batchResult.escalated}</strong></span>
          <span style={{ color: 'var(--warn)' }}>Awaiting customer: <strong>{batchResult.waiting}</strong></span>
          <span style={{ color: 'var(--text-muted)' }}>Skipped (cooldown/terminal): <strong>{batchResult.skipped}</strong></span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
        <KpiCard label="Revenue at Risk" value={summary.revenue_at_risk} accent="var(--risk)" />
        <KpiCard label="Revenue Recovered" value={summary.revenue_recovered} accent="var(--accent)" />
        <KpiCard label="Recovery Rate" value={summary.recovery_rate} format="percent" />
        <KpiCard label="Unrecovered Revenue" value={summary.unrecovered_revenue} />
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
        <KpiCard label="Failed Payments" value={summary.failed_payment_cases} format="count" />
        <KpiCard label="Checkout Drop-offs" value={summary.checkout_dropoff_cases} format="count" />
        <KpiCard label="Failed Subscriptions" value={summary.failed_subscription_cases} format="count" />
        <KpiCard label="Recovered Cases" value={summary.recovered_cases} format="count" accent="var(--accent)" />
        <KpiCard label="Pending Cases" value={summary.pending_cases} format="count" accent="var(--warn)" />
        <KpiCard label="Escalated Cases" value={summary.escalated_cases} format="count" accent="var(--risk)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.4fr) minmax(0,1fr)', gap: 16, marginBottom: 20 }}>
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 16 }}>Revenue at risk vs. recovered, by scenario</h3>
          <RecoveryByScenarioChart data={charts?.recovery_by_scenario} />
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 16 }}>Case status distribution</h3>
          <CaseStatusChart data={charts?.case_status_distribution} />
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 14, marginBottom: 16 }}>Recent recovery activity</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(charts?.recent_activity || []).slice(0, 10).map((a) => (
            <div key={`${a.recovery_case_id}-${a.created_at}-${a.event}`}
                 style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '8px 0', borderBottom: '1px solid var(--border-soft)' }}>
              <span>
                <span className="mono" style={{ color: 'var(--text-faint)', marginRight: 8 }}>
                  {a.recovery_case_id ? `#${a.recovery_case_id}` : ''}
                </span>
                {a.event}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>{fmtTime(a.created_at)}</span>
            </div>
          ))}
          {(!charts?.recent_activity || charts.recent_activity.length === 0) && (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No activity yet — run batch recovery to get started.</div>
          )}
        </div>
      </div>
    </>
  )
}
