import { useState } from 'react'
import { updateAlertStatus } from '../api.js'

const DEPT_TABS = [
  { key: 'summary',   label: '요약' },
  { key: 'cs',        label: 'CS' },
  { key: 'planning',  label: '기획' },
  { key: 'marketing', label: '마케팅' },
  { key: 'business',  label: '사업' },
]

const SEVERITY_HEADER = {
  CRITICAL: 'bg-red-500 text-white',
  WARNING:  'bg-yellow-400 text-yellow-900',
  INFO:     'bg-blue-500 text-white',
}

const ALERT_TYPE_LABEL = {
  sentiment_drop: '부정 리뷰 비율 급증',
  volume_spike:   '리뷰 볼륨 급증',
  keyword_alert:  '긴급 키워드 감지',
}

const NEXT_STATUS       = { new: 'acknowledged', acknowledged: 'resolved' }
const NEXT_STATUS_LABEL = { new: '확인됨으로 변경', acknowledged: '해결됨으로 변경' }

function DetailMetrics({ alertType, detail }) {
  if (!detail) return null
  const entries = Object.entries(detail).filter(([k]) => k !== 'window_hours')

  const labelMap = {
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

  const formatValue = (key, val) => {
    if (Array.isArray(val)) return val.join(', ')
    if (typeof val !== 'number') return String(val)
    if (key.includes('ratio') || key === 'diff') return `${(val * 100).toFixed(1)}%`
    if (key.includes('rate')) return `${val.toFixed(1)}/h`
    return val
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {entries.map(([key, val]) => (
        <div key={key} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
            {labelMap[key] || key}
          </p>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            {formatValue(key, val)}
          </p>
        </div>
      ))}
    </div>
  )
}

// prop을 alertData로 받아 window.alert()와 이름 충돌을 방지한다
export default function AlertDetail({ alert: alertData, onClose, onStatusChange }) {
  const [activeTab, setActiveTab] = useState('summary')
  const [updating, setUpdating] = useState(false)

  const recs       = alertData.recommendations || {}
  const nextStatus = NEXT_STATUS[alertData.status]

  const handleStatusChange = async () => {
    if (!nextStatus) return
    setUpdating(true)
    try {
      const updated = await updateAlertStatus(alertData.id, nextStatus)
      onStatusChange(updated)
    } catch {
      window.alert('상태 변경에 실패했습니다.')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* 오버레이 */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* 패널 */}
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-800 shadow-2xl flex flex-col overflow-hidden">
        {/* 헤더 */}
        <div className={`px-5 py-4 ${SEVERITY_HEADER[alertData.severity] || 'bg-gray-600 text-white'}`}>
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs font-medium opacity-80 mb-1">
                {alertData.game_name} · {ALERT_TYPE_LABEL[alertData.alert_type] || alertData.alert_type}
              </p>
              <p className="font-semibold text-sm leading-snug">{alertData.title}</p>
            </div>
            <button onClick={onClose} className="text-xl leading-none opacity-70 hover:opacity-100 mt-0.5">
              ✕
            </button>
          </div>
        </div>

        {/* 감지 수치 */}
        <div className="px-5 pt-4 pb-3 border-b border-gray-200 dark:border-gray-700">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            감지 데이터
          </p>
          <DetailMetrics alertType={alertData.alert_type} detail={alertData.detail} />
        </div>

        {/* 대응 방안 탭 */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 px-5">
          {DEPT_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`py-2.5 px-3 text-xs font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 탭 내용 */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {activeTab === 'summary' ? (
            <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
              {recs.summary || '대응 방안이 생성되지 않았습니다.'}
            </p>
          ) : (
            <ul className="space-y-2">
              {(recs[activeTab] || []).map((item, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-700 dark:text-gray-200">
                  <span className="text-indigo-500 font-bold shrink-0">{i + 1}.</span>
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
              {!recs[activeTab]?.length && (
                <p className="text-sm text-gray-400">내용이 없습니다.</p>
              )}
            </ul>
          )}
        </div>

        {/* 하단 상태 변경 */}
        {nextStatus ? (
          <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={handleStatusChange}
              disabled={updating}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {updating ? '처리 중...' : NEXT_STATUS_LABEL[alertData.status]}
            </button>
          </div>
        ) : alertData.status === 'resolved' ? (
          <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-center text-sm text-green-600 dark:text-green-400 font-medium">해결 완료</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
