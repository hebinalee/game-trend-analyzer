import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import GameDetail from './pages/GameDetail.jsx'
import Compare from './pages/Compare.jsx'
import Alerts from './pages/Alerts.jsx'
import { getAlertsUnreadCount } from './api.js'

export default function App() {
  const [dark, setDark] = useState(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )
  const [criticalCount, setCriticalCount] = useState(0)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  useEffect(() => {
    const fetchCount = () =>
      getAlertsUnreadCount()
        .then(data => setCriticalCount(data.critical))
        .catch(() => {})
    fetchCount()
    const timer = setInterval(fetchCount, 60000) // 1분마다 갱신
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
            Game Trend Analyzer
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400">
              대시보드
            </Link>
            <Link to="/compare" className="text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400">
              비교
            </Link>
            <Link to="/alerts" className="relative text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400">
              이슈
              {criticalCount > 0 && (
                <span className="absolute -top-1.5 -right-3.5 min-w-[16px] h-4 px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {criticalCount}
                </span>
              )}
            </Link>
            <button
              onClick={() => setDark(d => !d)}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 text-sm"
            >
              {dark ? '라이트' : '다크'}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/game/:id" element={<GameDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/alerts" element={<Alerts />} />
        </Routes>
      </main>
    </div>
  )
}
