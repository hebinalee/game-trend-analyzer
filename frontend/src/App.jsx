import { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  GitCompare,
  Bell,
  Moon,
  Sun,
  TrendingUp,
} from 'lucide-react'
import Dashboard from './pages/Dashboard.jsx'
import GameDetail from './pages/GameDetail.jsx'
import Compare from './pages/Compare.jsx'
import Alerts from './pages/Alerts.jsx'
import { getAlertsUnreadCount } from './api.js'
import { ToastProvider } from './components/Toast.jsx'

const NAV_ITEMS = [
  { to: '/',        icon: LayoutDashboard, label: '대시보드' },
  { to: '/compare', icon: GitCompare,      label: '비교'     },
  { to: '/alerts',  icon: Bell,            label: '이슈'     },
]

function NavItem({ to, icon: Icon, label, criticalCount, isActive }) {
  return (
    <Link
      to={to}
      className={[
        'relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150',
        isActive
          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/30'
          : 'text-slate-400 hover:text-white hover:bg-white/10',
      ].join(' ')}
    >
      <Icon size={18} strokeWidth={2} className="shrink-0" />
      <span>{label}</span>

      {/* Critical count badge on Bell icon */}
      {to === '/alerts' && criticalCount > 0 && (
        <span className="ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
          {criticalCount > 99 ? '99+' : criticalCount}
        </span>
      )}
    </Link>
  )
}

function Sidebar({ dark, setDark, criticalCount }) {
  const location = useLocation()

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col bg-slate-900 dark:bg-slate-950 border-r border-slate-800">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 shadow-lg shadow-indigo-900/40">
          <TrendingUp size={18} strokeWidth={2.5} className="text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent leading-none">
            게임 동향 기상청
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5 truncate">
            Game Trend Analyzer (GTA)
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(item => (
          <NavItem
            key={item.to}
            {...item}
            criticalCount={criticalCount}
            isActive={
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to)
            }
          />
        ))}
      </nav>

      {/* Dark mode toggle */}
      <div className="px-3 py-4 border-t border-slate-800">
        <button
          onClick={() => setDark(d => !d)}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-white/10 transition-all duration-150"
        >
          {dark ? (
            <>
              <Sun size={18} strokeWidth={2} className="shrink-0" />
              <span>라이트 모드</span>
            </>
          ) : (
            <>
              <Moon size={18} strokeWidth={2} className="shrink-0" />
              <span>다크 모드</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

function MobileTopBar({ dark, setDark, criticalCount }) {
  const location = useLocation()

  return (
    <header className="md:hidden sticky top-0 z-40 flex items-center justify-between bg-slate-900 px-4 py-3 border-b border-slate-800">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600">
          <TrendingUp size={15} strokeWidth={2.5} className="text-white" />
        </div>
        <span className="text-sm font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          게임 동향 기상청
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex items-center gap-1">
        {NAV_ITEMS.map(item => {
          const isActive =
            item.to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              className={[
                'relative flex items-center justify-center h-8 w-8 rounded-lg transition-all duration-150',
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-white/10',
              ].join(' ')}
            >
              <item.icon size={16} strokeWidth={2} />
              {item.to === '/alerts' && criticalCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
                  {criticalCount > 9 ? '9+' : criticalCount}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Dark mode toggle */}
      <button
        onClick={() => setDark(d => !d)}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all duration-150"
      >
        {dark ? <Sun size={16} strokeWidth={2} /> : <Moon size={16} strokeWidth={2} />}
      </button>
    </header>
  )
}

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
    <ToastProvider>
      <div className="flex h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 overflow-hidden">
        {/* Desktop sidebar */}
        <Sidebar dark={dark} setDark={setDark} criticalCount={criticalCount} />

        {/* Right side: mobile topbar + scrollable content */}
        <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
          <MobileTopBar dark={dark} setDark={setDark} criticalCount={criticalCount} />

          <div className="flex-1 overflow-auto">
            <main className="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-8">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/game/:id" element={<GameDetail />} />
                <Route path="/compare" element={<Compare />} />
                <Route path="/alerts" element={<Alerts />} />
              </Routes>
            </main>
          </div>
        </div>
      </div>
    </ToastProvider>
  )
}
