import { useEffect, useState, useCallback } from 'react'
import { Download } from 'lucide-react'
import { api } from '../api/client.js'
import AuditTimeline from '../components/audit/AuditTimeline.jsx'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'

export default function AuditTrail() {
  const [logs, setLogs] = useState(null)
  const [error, setError] = useState(null)
  const [caseIdFilter, setCaseIdFilter] = useState('')

  const load = useCallback((caseId) => {
    api.audit(caseId ? { case_id: caseId } : {})
      .then((r) => { setLogs(r.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not load audit trail.'))
  }, [])

  useEffect(() => { load() }, [load])

  const handleFilterSubmit = (e) => {
    e.preventDefault()
    load(caseIdFilter || undefined)
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Audit Trail</h1>
          <div className="page-subtitle">Every AI recommendation, guardrail decision, and executed action — immutable and timestamped.</div>
        </div>
        <a className="btn" href={api.auditExportUrl(caseIdFilter ? { case_id: caseIdFilter } : {})} download>
          <Download size={15} /> Export CSV
        </a>
      </div>

      <form onSubmit={handleFilterSubmit} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={caseIdFilter}
          onChange={(e) => setCaseIdFilter(e.target.value)}
          placeholder="Filter by case ID…"
          style={{
            background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6,
            padding: '8px 12px', color: 'var(--text)', fontSize: 13, width: 200,
          }}
        />
        <button className="btn" type="submit">Filter</button>
        {caseIdFilter && (
          <button className="btn" type="button" onClick={() => { setCaseIdFilter(''); load() }}>Clear</button>
        )}
      </form>

      {error && !logs && <ErrorState message={error} onRetry={() => load()} />}
      {!logs && !error && <LoadingSpinner label="Loading audit trail…" />}
      {logs && <AuditTimeline logs={logs} />}
    </>
  )
}
