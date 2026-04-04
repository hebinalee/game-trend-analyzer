import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
})

export const getGames = () => api.get('/games').then(r => r.data)

export const getReports = (gameId, startDate, endDate) => {
  const params = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  return api.get(`/reports/${gameId}`, { params }).then(r => r.data)
}

export const getLatestReport = (gameId) =>
  api.get(`/reports/${gameId}/latest`).then(r => r.data)

export const getDashboardSummary = () =>
  api.get('/dashboard/summary').then(r => r.data)

export const compareGames = (gameIds, date) =>
  api.get('/compare', { params: { game_ids: gameIds.join(','), date } }).then(r => r.data)

export const triggerCrawl = () => api.post('/admin/trigger-crawl').then(r => r.data)

export const triggerAnalyze = () => api.post('/admin/trigger-analyze').then(r => r.data)
