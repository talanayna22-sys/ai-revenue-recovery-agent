import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import FailedPayments from './pages/FailedPayments.jsx'
import CheckoutDropoffs from './pages/CheckoutDropoffs.jsx'
import FailedSubscriptions from './pages/FailedSubscriptions.jsx'
import AiAgent from './pages/AiAgent.jsx'
import AuditTrail from './pages/AuditTrail.jsx'
import Guardrails from './pages/Guardrails.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/failed-payments" element={<FailedPayments />} />
        <Route path="/checkout-dropoffs" element={<CheckoutDropoffs />} />
        <Route path="/failed-subscriptions" element={<FailedSubscriptions />} />
        <Route path="/ai-agent" element={<AiAgent />} />
        <Route path="/audit-trail" element={<AuditTrail />} />
        <Route path="/guardrails" element={<Guardrails />} />
      </Route>
    </Routes>
  )
}
