import { useState } from 'react'
import {
  AlertOctagon, AlertTriangle, Info, X,
  BarChart2, Headphones, Layers, Megaphone, Briefcase, FileText,
  Loader2, CheckCircle,
} from 'lucide-react'
import { updateAlertStatus } from '../api.js'

const DEPT_TABS = [
  { key: 'summary',   label: '요약',    Icon: FileText },
  { key: 'cs',        label: 'CS',      Icon: Headphones },
  { key: 'planning',  label: '기획',    Icon: Layers },
  { key: 'marketing', label: '마케팅',  Icon: Megaphone },
  { key: 'business',  label: '사업',    Icon: Briefcase },
]

const SEVERITY_CONFIG = {
  CRITICAL: {
    header: 'from-red-600 to-red-700',
    Icon: AlertOctagon,
  },
  WARNING: {
    header: 'from-amber-500 to-amber-600',
    Icon: AlertTriangle,
  },
  INFO: {
    header: 'from-blue-600 to-blue-700',
    Icon: Info,
  },
}

const ALERT_TYPE_LABEL = {
  sentiment_drop: '부정 리뷰 비율 급증',
  volume_spike:   '리뷰 볼륨 급증',
  keyword_alert:  '긴급 키워드 감지',
}

const NEXT_STATUS       = { new: 'acknowledged', acknowledged: 'resolved' }
const NEXT_STATUS_LABEL = { new: '확인됨으로 변경', acknowledged: '해결됨으로 변경' }
const NEXT_STATUS_CLS   = {
  new:          'bg-indigo-600 hover:bg-indigo-700',
  acknowledged: 'bg-green-600 hover:bg-green-700',
}

const METRIC_LABEL = {
  current_negative_ratio:  '현재 부정 비율',
  baseline_negative_ratio: '직전 부정 비율',
  diff:                    '변화량',
  current_reviews:         '현재 리뷰 수',
  baseline_reviews:        '직전 리뷰 수',
  current_hourly_rate:     '현재 리뷰 수/h',
  baseline_hourly_rate:    '직전 리뷰 수/h',
  ratio:                   '급증 배율',
  current_review_count:    '현재 리뷰 수',
  matched_keywords:        '감지 키워드',
  keyword_ratio:           '키워드 비율',
  total_posts:             '전체 포스트',
}

function formatMetricValue(key, val) {
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val !== 'number') return String(val)
  if (key.includes('ratio') || key === 'diff') return `${(val * 100).toFixed(1)}%`
  if (key.includes('rate')) return `${val.toFixed(1)}/h`
  return String(val)
}

function isHighlightMetric(key) {
  return key.includes('ratio') || key === 'diff' || key.includes('rate')
}

function DetailMetrics({ detail }) {
  if (!detail) return null
  const entries = Object.entries(detail).filter(([k]) => k !== 'window_hours')
  if (entries.length === 0) return null

  return (
    <div className="grid grid-cols-2 gap-2.5">
      {entries.map(([key, val]) => (
        <div key={key} className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
            {METRIC_LABEL[key] || key}
          </p>
          <p className={`text-sm font-semibold ${
            isHighlightMetric(key)
              ? 'text-indigo-600 dark:text-indigo-400'
              : 'text-slate-800 dark:text-slate-100'
          }`}>
            {formatMetricValue(key, val)}
          </p>
        </div>
      ))}
    </div>
  )
}

// prop을 alertData로 받아 window.alert()와 이름 충돌을 방지한다
export default function AlertDetail({ alert: alertData, onClose, onStatusChange }) {
  const [activeTab, setActiveTab] = useState('summary')
  const [updating, setUpdating]   = useState(false)
  const [errorMsg, setErrorMsg]   = useState('')

  const recs       = alertData.recommendations || {}
  const nextStatus = NEXT_STATUS[alertData.status]
  const sevCfg     = SEVERITY_CONFIG[alertData.severity] || SEVERITY_CONFIG.INFO
  const SevIcon    = sevCfg.Icon

  const handleStatusChange = async () => {
    if (!nextStatus) return
    setUpdating(true)
    setErrorMsg('')
    try {
      const updated = await updateAlertStatus(alertData.id, nextStatus)
      onStatusChange(updated)
    } catch {
      setErrorMsg('상태 변경에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in panel */}
      <div
        className="relative w-full max-w-lg bg-white dark:bg-slate-800 shadow-2xl flex flex-col overflow-hidden
                   animate-[slideInRight_0.25s_ease-out]"
        style={{ animationFillMode: 'both' }}
      >
        {/* Severity gradient header */}
        <div className={`bg-gradient-to-br ${sevCfg.header} px-5 py-5 text-white`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <SevIcon size={32} strokeWidth={1.75} className="shrink-0 mt-0.5 opacity-90" />
              <div className="min-w-0">
                <p className="text-xs font-medium opacity-75 mb-1">
                  {alertData.game_name}
                  <span className="mx-1.5 opacity-50">·</span>
                  {ALERT_TYPE_LABEL[alertData.alert_type] || alertData.alert_type}
                </p>
                <p className="font-bold text-base leading-snug">{alertData.title}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full
                         bg-white/10 hover:bg-white/25 transition-colors mt-0.5"
              aria-label="닫기"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Detection metrics */}
        <div className="px-5 pt-4 pb-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-1.5 mb-3">
            <BarChart2 size={13} className="text-slate-400 dark:text-slate-500" />
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              감지 데이터
            </span>
          </div>
          <DetailMetrics detail={alertData.detail} />
        </div>

        {/* Dept tabs */}
        <div className="flex gap-1 px-5 pt-3 pb-2 border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
          {DEPT_TABS.map(({ key, label, Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                          whitespace-nowrap transition-all duration-150 ${
                activeTab === key
                  ? 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {activeTab === 'summary' ? (
            <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
              {recs.summary || '대응 방안이 생성되지 않았습니다.'}
            </p>
          ) : (
            <ul className="space-y-2.5">
              {(recs[activeTab] || []).map((item, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-slate-700 dark:text-slate-200">
                  <span className="shrink-0 w-5 h-5 flex items-center justify-center rounded-full
                                   bg-indigo-100 dark:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400
                                   text-xs font-bold">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed pt-0.5">{item}</span>
                </li>
              ))}
              {!recs[activeTab]?.length && (
                <p className="text-sm text-slate-400 dark:text-slate-500">내용이 없습니다.</p>
              )}
            </ul>
          )}
        </div>

        {/* Footer: status action */}
        <div className="px-5 py-4 border-t border-slate-200 dark:border-slate-700">
          {errorMsg && (
            <p className="text-xs text-red-500 dark:text-red-400 mb-2 text-center">{errorMsg}</p>
          )}
          {nextStatus ? (
            <button
              onClick={handleStatusChange}
              disabled={updating}
              className={`w-full py-2.5 rounded-xl text-white text-sm font-semibold
                          disabled:opacity-60 transition-colors inline-flex items-center justify-center gap-2
                          ${NEXT_STATUS_CLS[alertData.status]}`}
            >
              {updating
                ? <><Loader2 size={15} className="animate-spin" /> 처리 중...</>
                : NEXT_STATUS_LABEL[alertData.status]
              }
            </button>
          ) : alertData.status === 'resolved' ? (
            <div className="flex items-center justify-center gap-2 py-1.5">
              <CheckCircle size={17} className="text-green-500" />
              <span className="text-sm font-semibold text-green-600 dark:text-green-400">해결 완료</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
