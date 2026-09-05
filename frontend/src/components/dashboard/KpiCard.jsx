const fmtINR = (n) =>
  '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })

export default function KpiCard({ label, value, format = 'currency', accent, sub }) {
  const display = format === 'currency' ? fmtINR(value)
    : format === 'percent' ? `${Number(value || 0).toFixed(1)}%`
    : Number(value || 0).toLocaleString('en-IN')

  return (
    <div className="card" style={{ flex: 1, minWidth: 200 }}>
      <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 10 }}>{label}</div>
      <div
        style={{
          fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700,
          color: accent || 'var(--text)', letterSpacing: '-0.01em',
        }}
      >
        {display}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-faint)', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}
