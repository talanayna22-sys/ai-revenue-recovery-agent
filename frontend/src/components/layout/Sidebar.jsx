import { NavLink } from 'react-router-dom'
import {
  LayoutGrid, CreditCard, ShoppingCart, RefreshCw, Bot, ScrollText, ShieldCheck,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid, end: true },
  { to: '/failed-payments', label: 'Failed Payments', icon: CreditCard },
  { to: '/checkout-dropoffs', label: 'Checkout Drop-offs', icon: ShoppingCart },
  { to: '/failed-subscriptions', label: 'Failed Subscriptions', icon: RefreshCw },
  { to: '/ai-agent', label: 'AI Agent', icon: Bot },
  { to: '/audit-trail', label: 'Audit Trail', icon: ScrollText },
  { to: '/guardrails', label: 'Guardrails', icon: ShieldCheck },
]

export default function Sidebar() {
  return (
    <aside
      style={{
        width: 232,
        flexShrink: 0,
        borderRight: '1px solid var(--border-soft)',
        padding: '22px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <div style={{ padding: '4px 10px 22px' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 19, fontWeight: 700, letterSpacing: '-0.02em' }}>
          Recoup
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text-faint)', marginTop: 2 }}>
          AI Revenue Recovery Agent
        </div>
      </div>

      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '9px 12px',
            borderRadius: 8,
            fontSize: 13.5,
            fontWeight: 500,
            color: isActive ? 'var(--text)' : 'var(--text-muted)',
            background: isActive ? 'var(--surface-raised)' : 'transparent',
          })}
        >
          <Icon size={16} strokeWidth={2} />
          {label}
        </NavLink>
      ))}
    </aside>
  )
}
