import { Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Sidebar from './Sidebar.jsx'
import { api } from '../../api/client.js'

export default function Layout() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api.health().then((r) => setHealth(r.data)).catch(() => setHealth({ status: 'error' }))
  }, [])

  const modeLabel = health?.payment_mode === 'razorpay_test' ? 'Razorpay Test Mode' : 'Synthetic Mode'

  return (
    <div className="app-shell">
      <Sidebar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 10,
            padding: '16px 36px 0',
          }}
        >
          {health && (
            <span
              className="mode-pill"
              style={{
                borderColor: health.status === 'ok' ? 'var(--border)' : 'var(--risk)',
                color: health.status === 'ok' ? 'var(--text-muted)' : 'var(--risk)',
              }}
              title={health.status === 'ok' ? `DB: ${health.database_engine}` : 'Backend unreachable'}
            >
              {health.status === 'ok' ? modeLabel : 'Backend offline'}
            </span>
          )}
        </div>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
