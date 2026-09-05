import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client.js'
import CaseTable, { fmtTime } from '../components/cases/CaseTable.jsx'
import CaseDetailDrawer from '../components/cases/CaseDetailDrawer.jsx'
import { LoadingSpinner, ErrorState } from '../components/common/EmptyState.jsx'

function minutesSince(abandonedAt) {
  if (!abandonedAt) return '—'
  const mins = Math.max(0, Math.round((Date.now() - new Date(abandonedAt.replace(' ', 'T'))) / 60000))
  return `${mins} min ago`
}

const COLUMNS = [
  { key: 'started_at', label: 'Checkout started', render: (c) => fmtTime(c.detail?.started_at) },
  { key: 'abandoned_at', label: 'Abandoned', render: (c) => minutesSince(c.detail?.abandoned_at) },
]

export default function CheckoutDropoffs() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  const load = useCallback(() => {
    api.listCases({ type: 'checkout_dropoff' })
      .then((r) => { setCases(r.data); setError(null) })
      .catch((e) => setError(e?.response?.data?.error || 'Could not load checkout drop-offs.'))
  }, [])

  useEffect(() => { load() }, [load])

  if (error && !cases) return <ErrorState message={error} onRetry={load} />
  if (!cases) return <LoadingSpinner label="Loading checkout drop-offs…" />

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Checkout Drop-offs</h1>
          <div className="page-subtitle">{cases.length} case{cases.length !== 1 ? 's' : ''} · carts started but never completed</div>
        </div>
      </div>
      <CaseTable
        cases={cases}
        columns={COLUMNS}
        onRowClick={(c) => setSelectedId(c.id)}
        emptyTitle="No checkout drop-offs"
        emptyDescription="Generate synthetic data from the Dashboard to populate this view."
      />
      {selectedId && (
        <CaseDetailDrawer caseId={selectedId} onClose={() => setSelectedId(null)} onChanged={load} />
      )}
    </>
  )
}
