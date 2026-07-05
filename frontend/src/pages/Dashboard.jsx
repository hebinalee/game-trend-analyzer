import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RefreshCw,
  Download,
  BarChart2,
  Monitor,
  Smartphone,
  Layers,
  AlertCircle,
  Gamepad2,
  Database,
  ShieldAlert,
} from 'lucide-react'
import { getDashboardSummary, triggerCrawl, triggerAnalyze, getAlerts } from '../api.js'
import ReportCard from '../components/ReportCard.jsx'

/* ─── Skeleton ─────────────────────────────────────────────────────────── */
function Skeleton() {
  return (
    <div className="animate-pulse bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5 h-56">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-slate-200 dark:bg-slate-700 rounded-xl" />
        <div className="flex flex-col gap-1.5 flex-1">
          <div className="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-28" />
          <div className="h-2.5 bg-slate-100 dark:bg-slate-700/60 rounded w-12" />
        </div>
      </div>
      <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full mb-2" />
      <div className="flex gap-2 mb-3">
        <div className="h-2 bg-slate-100 dark:bg-slate-700/60 rounded w-14" />
        <div className="h-2 bg-slate-100 dark:bg-slate-700/60 rounded w-14" />
        <div className="h-2 bg-slate-100 dark:bg-slate-700/60 rounded w-14" />
      </div>
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full mb-2" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-4/5 mb-4" />
      <div className="flex gap-1">
        <div className="h-5 bg-slate-100 dark:bg-slate-700/60 rounded-full w-16" />
        <div className="h-5 bg-slate-100 dark:bg-slate-700/60 rounded-full w-20" />
      </div>
    </div>
  )
}

/* ─── Platform tabs config ──────────────────────────────────────────────── */
const PLATFORM_FILTERS = [
  { key: 'all',    label: '전체',     Icon: Layers },
  { key: 'steam',  label: 'PC',       Icon: Monitor },
  { key: 'mobile', label: '모바일',   Icon: Smartphone },
]

/* ─── Toast ─────────────────────────────────────────────────────────────── */
function Toast({ msg, type }) {
  if (!msg) return null
  const base = 'fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium transition-all'
  const color = type === 'error'
    ? 'bg-red-600 text-white'
    : 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900'
  return (
    <div className={`${base} ${color}`}>
      {msg}
    </div>
  )
}

/* ─── Stat card ─────────────────────────────────────────────────────────── */
function StatCard({ Icon, value, label, iconCls }) {
  return (
    <div className="flex items-center gap-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 px-5 py-4 shadow-sm">
      <div className={`flex items-center justify-center w-10 h-10 rounded-xl ${iconCls}`}>
        <Icon size={20} strokeWidth={1.75} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 leading-none">{value}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{label}</p>
      </div>
    </div>
  )
}

/* ─── Dashboard ─────────────────────────────────────────────────────────── */
export default function Dashboard() {
  const [items, setItems]               = useState([])
  const [alertsByGame, setAlertsByGame] = useState({})
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState(null)
  const [lastUpdate, setLastUpdate]     = useState(null)
  const [platformFilter, setPlatformFilter] = useState('all')
  const [toast, setToast]               = useState({ msg: '', type: 'info' })
  const navigate = useNavigate()

  /* Show a temporary toast message */
  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast({ msg: '', type: 'info' }), 3000)
  }, [])

  /* Load dashboard data */
  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      getDashboardSummary(),
      getAlerts({ status: 'new', limit: 100 }),
    ])
      .then(([summary, alerts]) => {
        setItems(summary)
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
      .catch(err => {
        console.error('Dashboard load error:', err)
        setError('데이터를 불러오지 못했습니다.')
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  /* Admin action handlers */
  const handleTriggerCrawl = () => {
    triggerCrawl()
      .then(() => showToast('크롤링이 시작되었습니다.', 'info'))
      .catch(err => {
        console.error('Crawl trigger error:', err)
        showToast('크롤링 시작에 실패했습니다.', 'error')
      })
  }

  const handleTriggerAnalyze = () => {
    triggerAnalyze()
      .then(() => showToast('분석이 시작되었습니다.', 'info'))
      .catch(err => {
        console.error('Analyze trigger error:', err)
        showToast('분석 시작에 실패했습니다.', 'error')
      })
  }

  /* Derived stats */
  const totalGames   = items.length
  const totalPosts   = items.reduce((acc, i) => acc + (i.post_count || 0), 0)
  const activeIssues = Object.keys(alertsByGame).length

  /* Filtered items */
  const filteredItems = platformFilter === 'all'
    ? items
    : items.filter(item => item.platform === platformFilter)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">

        {/* ── Page header ── */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              게임 유저 동향
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              실시간 감성 분석 및 트렌드 모니터링
            </p>
            {lastUpdate && (
              <p className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 mt-2">
                <RefreshCw size={11} strokeWidth={2} />
                마지막 업데이트: {lastUpdate}
              </p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={handleTriggerCrawl}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-xl border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-indigo-50 hover:border-indigo-400 hover:text-indigo-700 dark:hover:bg-indigo-900/20 dark:hover:border-indigo-500 dark:hover:text-indigo-400 transition-all duration-150 shadow-sm"
            >
              <Download size={14} strokeWidth={2} />
              크롤링
            </button>
            <button
              onClick={handleTriggerAnalyze}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-xl border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-indigo-50 hover:border-indigo-400 hover:text-indigo-700 dark:hover:bg-indigo-900/20 dark:hover:border-indigo-500 dark:hover:text-indigo-400 transition-all duration-150 shadow-sm"
            >
              <BarChart2 size={14} strokeWidth={2} />
              분석
            </button>
          </div>
        </div>

        {/* ── Stats summary row ── */}
        {!loading && !error && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <StatCard
              Icon={Gamepad2}
              value={totalGames}
              label="모니터링 게임 수"
              iconCls="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
            />
            <StatCard
              Icon={Database}
              value={totalPosts.toLocaleString()}
              label="오늘 수집된 데이터"
              iconCls="bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
            />
            <StatCard
              Icon={ShieldAlert}
              value={activeIssues}
              label="활성 이슈"
              iconCls="bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
            />
          </div>
        )}

        {/* ── Error banner ── */}
        {error && (
          <div className="flex items-center justify-between gap-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl px-4 py-3.5 mb-6">
            <div className="flex items-center gap-2.5 text-red-600 dark:text-red-400">
              <AlertCircle size={16} strokeWidth={2} />
              <span className="text-sm font-medium">{error}</span>
            </div>
            <button
              onClick={load}
              className="text-xs font-medium text-red-600 dark:text-red-400 underline underline-offset-2 hover:no-underline flex-shrink-0"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* ── Platform filter tabs ── */}
        <div className="inline-flex bg-slate-100 dark:bg-slate-800 rounded-xl p-1 mb-6 gap-0.5">
          {PLATFORM_FILTERS.map(({ key, label, Icon }) => {
            const count = key === 'all' ? items.length : items.filter(i => i.platform === key).length
            const active = platformFilter === key
            return (
              <button
                key={key}
                onClick={() => setPlatformFilter(key)}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
                  active
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
              >
                <Icon size={14} strokeWidth={active ? 2 : 1.75} />
                {label}
                {!loading && (
                  <span
                    className={`text-[11px] px-1.5 py-0.5 rounded-full font-medium ${
                      active
                        ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400'
                        : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* ── Game card grid ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {loading
            ? Array.from({ length: 12 }).map((_, i) => <Skeleton key={i} />)
            : filteredItems.map(item => (
              <ReportCard
                key={item.game_id}
                game={{
                  id: item.game_id,
                  name: item.game_name,
                  platform: item.platform,
                  thumbnail_url: item.thumbnail_url,
                }}
                report={item.summary ? item : null}
                alertSeverity={alertsByGame[item.game_id] || null}
                onClick={() => navigate(`/game/${item.game_id}`)}
              />
            ))
          }
        </div>
      </div>

      {/* ── Floating toast ── */}
      <Toast msg={toast.msg} type={toast.type} />
    </div>
  )
}
