import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

export const api = {
  health: () => client.get('/health'),

  dashboardSummary: () => client.get('/dashboard/summary'),
  dashboardCharts: () => client.get('/dashboard/charts'),

  listCases: (params) => client.get('/cases', { params }),
  getCase: (id) => client.get(`/cases/${id}`),
  executeRecovery: (id) => client.post(`/cases/${id}/execute-recovery`),
  getCaseActions: (id) => client.get(`/cases/${id}/actions`),
  getCaseAudit: (id) => client.get(`/cases/${id}/audit`),

  aiDecisions: (params) => client.get('/ai/decisions', { params }),

  audit: (params) => client.get('/audit', { params }),
  auditExportUrl: (params) => {
    const qs = new URLSearchParams(params || {}).toString()
    return `/api/audit/export.csv${qs ? `?${qs}` : ''}`
  },

  guardrails: () => client.get('/guardrails'),

  generateBatch: (body) => client.post('/demo/generate-batch', body || {}),
  runBatch: (body) => client.post('/demo/run-batch', body || {}),
}

export default client
