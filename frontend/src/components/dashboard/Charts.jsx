import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const SCENARIO_LABELS = {
  failed_payment: 'Failed Payments',
  checkout_dropoff: 'Checkout Drop-offs',
  failed_subscription: 'Failed Subscriptions',
}

const STATUS_COLORS = {
  DETECTED: '#6FA8FF',
  ANALYZING: '#6FA8FF',
  ACTION_TAKEN: '#6FA8FF',
  PENDING_RETRY: '#F5B85C',
  RECOVERED: '#35D0A0',
  ESCALATED: '#FF8066',
  STOPPED: '#5B667C',
}

const tooltipStyle = {
  background: '#1A2331', border: '1px solid #253044', borderRadius: 8, fontSize: 12.5,
}

export function RecoveryByScenarioChart({ data }) {
  const chartData = (data || []).map((d) => ({
    name: SCENARIO_LABELS[d.scenario_type] || d.scenario_type,
    'At Risk': d.at_risk,
    'Recovered': d.recovered,
  }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} barGap={6}>
        <CartesianGrid stroke="#1D2739" vertical={false} />
        <XAxis dataKey="name" stroke="#5B667C" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="#5B667C" fontSize={12} tickLine={false} axisLine={false}
               tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
        <Legend wrapperStyle={{ fontSize: 12.5 }} />
        <Bar dataKey="At Risk" fill="#FF8066" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Recovered" fill="#35D0A0" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function CaseStatusChart({ data }) {
  const chartData = (data || []).filter((d) => d.count > 0)
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={chartData} dataKey="count" nameKey="status" innerRadius={58} outerRadius={92} paddingAngle={2}>
          {chartData.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#5B667C'} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
