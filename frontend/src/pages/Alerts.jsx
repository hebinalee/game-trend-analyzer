import { useEffect, useState } from 'react'
import { getAlerts, getAlertDetail, getGames } from '../api.js'
import AlertCard from '../components/AlertCard.jsx'
import AlertDetail from '../components/AlertDetail.jsx'

const SEVERITY_TABS = [
  { key: '',         label: '전체' },
  { key: 'CRITICAL', label: '🚨 CRITICAL' },
  { key: 'WARNING',  label: '⚠️ WARNING' },
  { key: '__new__',  label: '미확인' },
]

function Skeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 h-24">
      <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-1/3 mb-2" />
      <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-full mb-1" />
      <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-2/3" />
    </div>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('')
  const [gameFilter, setGameFilter] = useState('')
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const fetchAlerts = (tab, game) => {
    setLoading(true)
    const params = {}
    if (tab === '__new__') params.status = 'new'
    else if (tab) params.severity = tab
    if (game) params.game_id = game
    getAlerts(params)
      .then(setAlerts)
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getGames().then(setGames).catch(() => {})
    fetchAlerts('', '')
  }, [])

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    fetchAlerts(tab, gameFilter)
  }

  const handleGameFilter = (gameId) => {
    setGameFilter(gameId)
    fetchAlerts(activeTab, gameId)
  }

  const handleCardClick = async (alertId) => {
    setDetailLoading(true)
    try {
      const detail = await getAlertDetail(alertId)
      setSelectedAlert(detail)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleStatusChange = (updated) => {
    setSelectedAlert(updated)
    setAlerts(prev => prev.map(a => a.id === updated.id ? { ...a, status: updated.status } : a))
  }

  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL' && a.status === 'new').length

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">이슈 트래킹</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            감지된 이상 이슈 및 대응 방안
          </p>
        </div>
        {criticalCount > 0 && (
          <span className="px-3 py-1 bg-red-500 text-white text-sm font-bold rounded-full">
            🚨 미확인 CRITICAL {criticalCount}건
          </span>
        )}
      </div>

      {/* 필터 영역 */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        {/* 심각도 탭 */}
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
          {SEVERITY_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === tab.key
                  ? 'bg-white dark:bg-gray-600 shadow text-gray-900 dark:text-gray-100'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 게임 필터 */}
        <select
          value={gameFilter}
          onChange={e => handleGameFilter(e.target.value)}
          className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
        >
          <option value="">전체 게임</option>
          {games.map(g => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
      </div>

      {/* 이슈 목록 */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-sm">감지된 이슈가 없습니다.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {alerts.map(alert => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onClick={() => handleCardClick(alert.id)}
            />
          ))}
        </div>
      )}

      {/* 상세 패널 */}
      {selectedAlert && (
        <AlertDetail
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onStatusChange={handleStatusChange}
        />
      )}
    </div>
  )
}
