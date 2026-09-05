import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client.js'
import CaseTable from '../components/cases/CaseTable.jsx'
import CaseDetailDrawer from '../components/cases/CaseDetailDrawer.jsx'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'

const COLUMNS = [
  { key: 'failure_reason', label: 'Failure reason', render: (c) => (c.detail?.failure_reason || '—').replaceAll('_', ' ') },
  { key: 'attempt_number', label: 'Attempts' },
  { key: 'payment_method', label: 'Method' },
]

export default function FailedPayments() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  const load = useCallback(() => {
    api.listCases({ type: 'failed_payment' })
      .then((r) => { setCases(r.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not load failed payments.'))
  }, [])

  useEffect(() => { load() }, [load])

  if (error && !cases) return <ErrorState message={error} onRetry={load} />
  if (!cases) return <LoadingSpinner label="Loading failed payments…" />

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Failed Payments</h1>
          <div className="page-subtitle">{cases.length} case{cases.length !== 1 ? 's' : ''} · payment attempts that did not go through</div>
        </div>
      </div>
      <CaseTable
        cases={cases}
        columns={COLUMNS}
        onRowClick={(c) => setSelectedId(c.id)}
        emptyTitle="No failed payments"
        emptyDescription="Generate synthetic data from the Dashboard to populate this view."
      />
      {selectedId && (
        <CaseDetailDrawer caseId={selectedId} onClose={() => setSelectedId(null)} onChanged={load} />
      )}
    </>
  )
}
