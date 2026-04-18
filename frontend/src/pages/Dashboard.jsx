import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboardSummary, triggerCrawl, triggerAnalyze, getAlerts } from '../api.js'
import ReportCard from '../components/ReportCard.jsx'

function Skeleton() {
  return (
    <div className="animate-pulse bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 h-44">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-gray-200 dark:bg-gray-600 rounded-lg" />
        <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-24" />
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded mb-3" />
      <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-full mb-2" />
      <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-3/4" />
    </div>
  )
}

export default function Dashboard() {
  const [items, setItems] = useState([])
  const [alertsByGame, setAlertsByGame] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      getDashboardSummary(),
      getAlerts({ status: 'new', limit: 100 }),
    ])
      .then(([summary, alerts]) => {
        setItems(summary)
        // game_id → 최고 severity 매핑 (CRITICAL > WARNING > INFO)
        const severityRank = { CRITICAL: 2, WARNING: 1, INFO: 0 }
        const map = {}
        alerts.forEach(a => {
          const cur = map[a.game_id]
          if (!cur || severityRank[a.severity] > severityRank[cur]) {
            map[a.game_id] = a.severity
          }
        })
        setAlertsByGame(map)
        setLastUpdate(new Date().toLocaleString('ko-KR'))
      })
      .catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleTriggerCrawl = () => {
    triggerCrawl().then(() => alert('크롤링이 시작되었습니다.')).catch(() => alert('오류 발생'))
  }

  const handleTriggerAnalyze = () => {
    triggerAnalyze().then(() => alert('분석이 시작되었습니다.')).catch(() => alert('오류 발생'))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">게임 유저 동향 대시보드</h1>
          {lastUpdate && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">마지막 업데이트: {lastUpdate}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleTriggerCrawl}
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            크롤링
          </button>
          <button
            onClick={handleTriggerAnalyze}
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            분석
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 flex items-center justify-between">
          <span className="text-red-600 dark:text-red-400">{error}</span>
          <button onClick={load} className="text-sm text-red-600 dark:text-red-400 underline">
            다시 시도
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} />)
          : items.map(item => (
            <ReportCard
              key={item.game_id}
              game={{ id: item.game_id, name: item.game_name, thumbnail_url: item.thumbnail_url }}
              report={item.summary ? item : null}
              alertSeverity={alertsByGame[item.game_id] || null}
              onClick={() => navigate(`/game/${item.game_id}`)}
            />
          ))
        }
      </div>
    </div>
  )
}
