export function LoadingSpinner({ label = 'Loading…' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '40px 0', color: 'var(--text-muted)' }}>
      <div className="spinner" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <h3 style={{ color: 'var(--text)', marginBottom: 6, fontSize: 15 }}>{title}</h3>
      {description && <p style={{ margin: 0, fontSize: 13 }}>{description}</p>}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="empty-state">
      <h3 style={{ color: 'var(--risk)', marginBottom: 6, fontSize: 15 }}>Something went wrong</h3>
      <p style={{ margin: '0 0 16px', fontSize: 13 }}>{message}</p>
      {onRetry && <button className="btn" onClick={onRetry}>Try again</button>}
    </div>
  )
}
