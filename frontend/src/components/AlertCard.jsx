import { AlertOctagon, AlertTriangle, Info, Activity, Gamepad2, Clock } from 'lucide-react'

const SEVERITY_CARD = {
  CRITICAL: 'border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10',
  WARNING:  'border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10',
  INFO:     'border-blue-200 dark:border-blue-800 bg-blue-50/20 dark:bg-blue-900/10',
}

const SEVERITY_BADGE = {
  CRITICAL: {
    cls:  'bg-red-500 text-white',
    Icon: AlertOctagon,
    label: 'CRITICAL',
  },
  WARNING: {
    cls:  'bg-amber-400 text-amber-900',
    Icon: AlertTriangle,
    label: 'WARNING',
  },
  INFO: {
    cls:  'bg-blue-500 text-white',
    Icon: Info,
    label: 'INFO',
  },
}

const STATUS_BADGE = {
  new:          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
  acknowledged: 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300',
  resolved:     'bg-green-100 dark:bg-green-900/60 text-green-700 dark:text-green-300',
}

const STATUS_LABEL = {
  new: '미확인', acknowledged: '확인됨', resolved: '해결됨',
}

const ALERT_TYPE_LABEL = {
  sentiment_drop: '부정 리뷰 급증',
  volume_spike:   '리뷰 볼륨 급증',
  keyword_alert:  '긴급 키워드 감지',
}

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60) return '방금 전'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export default function AlertCard({ alert, onClick }) {
  const sev = SEVERITY_BADGE[alert.severity] || SEVERITY_BADGE.INFO
  const SevIcon = sev.Icon

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border p-5 cursor-pointer hover:shadow-md transition-all duration-200 ${SEVERITY_CARD[alert.severity] || SEVERITY_CARD.INFO}`}
    >
      {/* Top row: severity badge + status badge */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${sev.cls}`}>
          <SevIcon size={11} strokeWidth={2.5} />
          {sev.label}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[alert.status] || STATUS_BADGE.new}`}>
          {STATUS_LABEL[alert.status] || alert.status}
        </span>
      </div>

      {/* Alert type */}
      <div className="flex items-center gap-1 mb-1.5">
        <Activity size={11} className="text-slate-400 dark:text-slate-500 shrink-0" />
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {ALERT_TYPE_LABEL[alert.alert_type] || alert.alert_type}
        </span>
      </div>

      {/* Title */}
      <p className="font-semibold text-sm leading-snug text-slate-800 dark:text-slate-100 mb-3 line-clamp-2">
        {alert.title}
      </p>

      {/* Bottom row: game name + time */}
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 truncate">
          <Gamepad2 size={11} />
          {alert.game_name}
        </span>
        <span className="inline-flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500 shrink-0">
          <Clock size={11} />
          {timeAgo(alert.detected_at)}
        </span>
      </div>
    </div>
  )
}
