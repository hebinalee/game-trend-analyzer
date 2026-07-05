import { useEffect, useState } from 'react'
import {
  AlertOctagon, Monitor, Smartphone, Layers, CheckCircle,
} from 'lucide-react'
import { getAlerts, getAlertDetail, getGames } from '../api.js'
import AlertCard from '../components/AlertCard.jsx'
import AlertDetail from '../components/AlertDetail.jsx'

/* ------------------------------------------------------------------ */
/* Constants                                                            */
/* ------------------------------------------------------------------ */

const SEVERITY_TABS = [
  {
    key: '',
    label: '전체',
    activeCls: 'bg-slate-700 text-white dark:bg-slate-200 dark:text-slate-800',
  },
  {
    key: 'CRITICAL',
    label: 'CRITICAL',
    activeCls: 'bg-red-500 text-white',
  },
  {
    key: 'WARNING',
    label: 'WARNING',
    activeCls: 'bg-amber-400 text-amber-900',
  },
  {
    key: '__new__',
    label: '미확인',
    activeCls: 'bg-indigo-600 text-white dark:bg-indigo-500',
  },
]

const PLATFORM_FILTERS = [
  { key: 'all',    label: '전체',      Icon: Layers },
  { key: 'steam',  label: 'PC',        Icon: Monitor },
  { key: 'mobile', label: '모바일',    Icon: Smartphone },
]

/* ------------------------------------------------------------------ */
/* Skeleton                                                             */
/* ------------------------------------------------------------------ */

function Skeleton() {
  return (
    <div className="animate-pulse rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 h-36">
      <div className="flex justify-between mb-3">
        <div className="h-5 bg-slate-200 dark:bg-slate-600 rounded-full w-20" />
        <div className="h-5 bg-slate-200 dark:bg-slate-600 rounded-full w-14" />
      </div>
      <div className="h-3.5 bg-slate-200 dark:bg-slate-600 rounded w-full mb-2" />
      <div className="h-3.5 bg-slate-200 dark:bg-slate-600 rounded w-3/4 mb-5" />
      <div className="flex justify-between">
        <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded w-24" />
        <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded w-16" />
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

export default function Alerts() {
  const [alerts, setAlerts]           = useState([])
  const [games, setGames]             = useState([])
  const [loading, setLoading]         = useState(true)
  const [gamesError, setGamesError]   = useState(false)
  const [activeTab, setActiveTab]     = useState('')
  const [platformFilter, setPlatformFilter] = useState('all')
  const [gameFilter, setGameFilter]   = useState('')
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  /* fetch ----------------------------------------------------------- */

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
    getGames()
      .then(setGames)
      .catch(() => setGamesError(true))
    fetchAlerts('', '')
  }, [])

  /* handlers -------------------------------------------------------- */

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    fetchAlerts(tab, gameFilter)
  }

  const handlePlatformFilter = (platform) => {
    setPlatformFilter(platform)
    setGameFilter('')
    fetchAlerts(activeTab, '')
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

  /* derived --------------------------------------------------------- */

  const criticalCount  = alerts.filter(a => a.severity === 'CRITICAL' && a.status === 'new').length
  const filteredGames  = platformFilter === 'all'
    ? games
    : games.filter(g => g.platform === platformFilter)

  /* ---------------------------------------------------------------- */

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 -m-4 sm:-m-6 p-4 sm:p-6">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">이슈 트래킹</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            감지된 이상 이슈 및 대응 방안
          </p>
        </div>

        {criticalCount > 0 && (
          <div className="flex items-center gap-1.5 bg-red-500 text-white px-3 py-1.5 rounded-full shadow-md shadow-red-200 dark:shadow-red-900/40 shrink-0">
            <AlertOctagon size={14} strokeWidth={2.5} />
            <span className="text-sm font-bold whitespace-nowrap">
              미확인 CRITICAL {criticalCount}건
            </span>
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">

          {/* Platform toggle */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-700 rounded-xl p-1">
            {PLATFORM_FILTERS.map(({ key, label, Icon }) => (
              <button
                key={key}
                onClick={() => handlePlatformFilter(key)}
                title={label}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                  platformFilter === key
                    ? 'bg-white dark:bg-slate-600 shadow text-slate-900 dark:text-slate-100'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
              >
                <Icon size={13} />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-slate-200 dark:bg-slate-600" />

          {/* Severity pill-tabs */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {SEVERITY_TABS.map(({ key, label, activeCls }) => (
              <button
                key={key}
                onClick={() => handleTabChange(key)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 ${
                  activeTab === key
                    ? activeCls
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-slate-200 dark:bg-slate-600 hidden sm:block" />

          {/* Game select */}
          <select
            value={gameFilter}
            onChange={e => handleGameFilter(e.target.value)}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-xl px-3 py-1.5
                       bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200
                       focus:outline-none focus:ring-2 focus:ring-indigo-400/50"
          >
            <option value="">전체 게임</option>
            {gamesError
              ? <option disabled>게임 목록 로드 실패</option>
              : filteredGames.map(g => (
                  <option key={g.id} value={String(g.id)}>{g.name}</option>
                ))
            }
          </select>

          {/* Loading indicator for detail fetch */}
          {detailLoading && (
            <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">불러오는 중...</span>
          )}
        </div>
      </div>

      {/* Alert grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-center">
          <CheckCircle size={48} className="text-green-500" strokeWidth={1.5} />
          <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">이슈 없음</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">현재 감지된 이슈가 없습니다.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {alerts.map(alert => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onClick={() => handleCardClick(alert.id)}
            />
          ))}
        </div>
      )}

      {/* Detail panel */}
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
