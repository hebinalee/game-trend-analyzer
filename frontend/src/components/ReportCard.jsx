import { Monitor, Smartphone, AlertTriangle, AlertCircle, BarChart2 } from 'lucide-react'
import { SENTIMENT } from '../colors.js'

const PLATFORM_META = {
  steam:  { label: 'PC',     Icon: Monitor,    cls: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800' },
  mobile: { label: 'Mobile', Icon: Smartphone, cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800' },
}

const ALERT_BADGE = {
  CRITICAL: {
    cls: 'bg-red-500 text-white',
    Icon: AlertTriangle,
    label: 'CRITICAL',
  },
  WARNING: {
    cls: 'bg-amber-400 text-amber-900',
    Icon: AlertCircle,
    label: 'WARNING',
  },
}

export default function ReportCard({ game, report, alertSeverity, onClick }) {
  const sentiment = report?.sentiment || {}
  const pos = Math.round((sentiment.positive || 0) * 100)
  const neg = Math.round((sentiment.negative || 0) * 100)
  const neu = Math.max(0, 100 - pos - neg)

  const platform = PLATFORM_META[game.platform] || PLATFORM_META.steam
  const PlatformIcon = platform.Icon
  const alertBadge = alertSeverity ? ALERT_BADGE[alertSeverity] : null

  return (
    <div
      onClick={onClick}
      className="relative flex flex-col bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5 cursor-pointer hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-500 transition-all duration-200 shadow-sm"
    >
      {/* Alert severity badge — top-right */}
      {alertBadge && (
        <span
          className={`absolute top-4 right-4 inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${alertBadge.cls}`}
          title={`${alertBadge.label} 이슈 감지`}
        >
          <alertBadge.Icon size={9} strokeWidth={2.5} />
          {alertBadge.label}
        </span>
      )}

      {/* Card header */}
      <div className="flex items-start gap-3 mb-4">
        {/* Thumbnail / fallback avatar */}
        <div className="relative flex-shrink-0">
          {game.thumbnail_url ? (
            <img
              src={game.thumbnail_url}
              alt={game.name}
              className="w-10 h-10 rounded-xl object-cover bg-slate-100 dark:bg-slate-700"
              onError={e => {
                e.currentTarget.style.display = 'none'
                e.currentTarget.nextSibling.style.display = 'flex'
              }}
            />
          ) : null}
          <div
            className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold text-sm"
            style={{ display: game.thumbnail_url ? 'none' : 'flex' }}
          >
            {game.name.slice(0, 2)}
          </div>
        </div>

        {/* Name + platform badge */}
        <div className="flex flex-col gap-1 min-w-0 pt-0.5">
          <h3
            className="font-semibold text-[15px] leading-tight truncate text-slate-900 dark:text-slate-100"
            style={{ paddingRight: alertBadge ? '4.5rem' : '0' }}
          >
            {game.name}
          </h3>
          <span
            className={`inline-flex items-center gap-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full border w-fit ${platform.cls}`}
          >
            <PlatformIcon size={9} strokeWidth={2.5} />
            {platform.label}
          </span>
        </div>
      </div>

      {/* Report content */}
      {report ? (
        <div className="flex flex-col gap-3 flex-1">
          {/* Sentiment section */}
          <div>
            <p className="text-[11px] font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1.5">
              감성 분포
            </p>
            {/* Stacked bar */}
            <div className="flex h-2.5 rounded-full overflow-hidden">
              {pos > 0 && (
                <div
                  style={{ width: `${pos}%`, backgroundColor: SENTIMENT.pos }}
                  title={`긍정 ${pos}%`}
                />
              )}
              {neu > 0 && (
                <div
                  style={{ width: `${neu}%`, backgroundColor: SENTIMENT.neu }}
                  title={`중립 ${neu}%`}
                />
              )}
              {neg > 0 && (
                <div
                  style={{ width: `${neg}%`, backgroundColor: SENTIMENT.neg }}
                  title={`부정 ${neg}%`}
                />
              )}
            </div>
            {/* Stat chips */}
            <div className="flex gap-2 mt-2">
              {[
                { label: '긍정', value: pos, color: SENTIMENT.pos },
                { label: '중립', value: neu, color: SENTIMENT.neu },
                { label: '부정', value: neg, color: SENTIMENT.neg },
              ].map(({ label, value, color }) => (
                <span
                  key={label}
                  className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  {label} {value}%
                </span>
              ))}
            </div>
          </div>

          {/* Summary */}
          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed line-clamp-2">
            {report.summary || '요약 없음'}
          </p>

          {/* Hot topics */}
          {(report.hot_topics || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-auto pt-1">
              {(report.hot_topics || []).slice(0, 3).map((topic, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-[11px] font-medium rounded-full border border-indigo-100 dark:border-indigo-800"
                >
                  #{topic}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* No-data state */
        <div className="flex flex-col items-center justify-center flex-1 py-6 gap-2 text-slate-300 dark:text-slate-600">
          <BarChart2 size={28} strokeWidth={1.5} />
          <p className="text-xs text-slate-400 dark:text-slate-500">분석 데이터 없음</p>
        </div>
      )}
    </div>
  )
}
