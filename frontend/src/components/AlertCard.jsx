const SEVERITY_STYLE = {
  CRITICAL: 'bg-red-100 dark:bg-red-900/40 border-red-300 dark:border-red-700',
  WARNING:  'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-300 dark:border-yellow-700',
  INFO:     'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700',
}

const SEVERITY_BADGE = {
  CRITICAL: 'bg-red-500 text-white',
  WARNING:  'bg-yellow-400 text-yellow-900',
  INFO:     'bg-blue-400 text-white',
}

const STATUS_BADGE = {
  new:          'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200',
  acknowledged: 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300',
  resolved:     'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
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
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border p-4 cursor-pointer hover:shadow-md transition-all ${SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.INFO}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${SEVERITY_BADGE[alert.severity]}`}>
            {alert.severity}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {ALERT_TYPE_LABEL[alert.alert_type] || alert.alert_type}
          </span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${STATUS_BADGE[alert.status]}`}>
          {STATUS_LABEL[alert.status] || alert.status}
        </span>
      </div>

      <p className="text-sm font-medium text-gray-800 dark:text-gray-100 mb-1 line-clamp-2">
        {alert.title}
      </p>

      <div className="flex items-center justify-between mt-2">
        <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
          {alert.game_name}
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {timeAgo(alert.detected_at)}
        </span>
      </div>
    </div>
  )
}
