import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { Bug, Star, Settings } from 'lucide-react'
import { SENTIMENT } from '../colors.js'

const COLORS = ['#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
const GRID_COLS = ['', 'grid-cols-1', 'grid-cols-1 sm:grid-cols-2', 'grid-cols-1 sm:grid-cols-3', 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4']
const S = SENTIMENT

function SentimentBar({ positive, neutral, negative }) {
  const pos = Math.round((positive || 0) * 100)
  const neu = Math.round((neutral || 0) * 100)
  const neg = Math.round((negative || 0) * 100)
  return (
    <div>
      <div className="flex rounded-full overflow-hidden h-2">
        <div style={{ width: `${pos}%`, backgroundColor: S.pos }} title={`긍정 ${pos}%`} />
        <div style={{ width: `${neu}%`, backgroundColor: S.neu }} title={`중립 ${neu}%`} />
        <div style={{ width: `${neg}%`, backgroundColor: S.neg }} title={`부정 ${neg}%`} />
      </div>
      <div className="flex gap-3 mt-1.5">
        <span className="flex items-center gap-1 text-xs" style={{ color: S.pos }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: S.pos }} />긍정 {pos}%
        </span>
        <span className="flex items-center gap-1 text-xs" style={{ color: S.neu }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: S.neu }} />중립 {neu}%
        </span>
        <span className="flex items-center gap-1 text-xs" style={{ color: S.neg }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: S.neg }} />부정 {neg}%
        </span>
      </div>
    </div>
  )
}

function IssueList({ icon: Icon, label, color, items }) {
  if (!items || items.length === 0) return null
  return (
    <div>
      <p className={`flex items-center gap-1 text-xs font-semibold mb-1.5 ${color}`}>
        {Icon && <Icon size={11} strokeWidth={2.5} />}
        {label}
      </p>
      <ul className="space-y-0.5">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-slate-600 dark:text-slate-400 flex gap-1.5">
            <span className="mt-0.5 shrink-0 text-slate-400">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function GameCard({ r, color, isExpanded, onToggle }) {
  const s = r.report?.sentiment || {}
  const issues = r.report?.key_issues || {}
  const hotTopics = r.report?.hot_topics || []
  const trendKeywords = r.report?.trend_keywords || []

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
      {/* 헤더 */}
      <div className="px-4 py-3 flex items-center gap-2" style={{ backgroundColor: color + '18', borderBottom: `3px solid ${color}` }}>
        <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
        <h4 className="font-bold text-sm truncate text-slate-800 dark:text-slate-100" title={r.game_name}>{r.game_name}</h4>
      </div>

      {r.report ? (
        <div className="p-4 space-y-4 flex-1">

          {/* 감성 분포 */}
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">감성 분포</p>
            <SentimentBar positive={s.positive} neutral={s.neutral} negative={s.negative} />
          </div>

          <hr className="border-slate-100 dark:border-slate-700" />

          {/* 요약 */}
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1.5">요약</p>
            <p className={`text-sm text-slate-700 dark:text-slate-300 leading-relaxed ${isExpanded ? '' : 'line-clamp-4'}`}>
              {r.report.summary || '요약 없음'}
            </p>
            <button
              onClick={onToggle}
              className="mt-1 text-xs font-medium text-indigo-500 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
            >
              {isExpanded ? '접기 ▲' : '더보기 ▼'}
            </button>
          </div>

          {/* 화제 */}
          {hotTopics.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1.5">화제</p>
              <div className="flex flex-wrap gap-1">
                {hotTopics.map((t, j) => (
                  <span key={j} className="px-2 py-0.5 text-xs rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 핵심 이슈 — 펼침 상태에서만 */}
          {isExpanded && (
            <div>
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">핵심 이슈</p>
              <div className="space-y-2.5 bg-slate-50 dark:bg-slate-900/40 rounded-xl p-3">
                <IssueList icon={Bug} label="버그" color="text-red-500" items={issues.bugs} />
                <IssueList icon={Star} label="요청사항" color="text-blue-500" items={issues.requests} />
                <IssueList icon={Settings} label="운영 이슈" color="text-amber-500" items={issues.operations} />
                {!issues.bugs?.length && !issues.requests?.length && !issues.operations?.length && (
                  <p className="text-xs text-slate-400">이슈 없음</p>
                )}
              </div>
            </div>
          )}

          {/* 트렌드 키워드 */}
          {trendKeywords.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1.5">트렌드 키워드</p>
              <div className="flex flex-wrap gap-1">
                {trendKeywords.map((t, j) => (
                  <span key={j} className="px-2 py-0.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 font-mono">
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}

        </div>
      ) : (
        <div className="p-4 text-sm text-slate-400 flex-1 flex items-center justify-center">
          해당 날짜 데이터 없음
        </div>
      )}
    </div>
  )
}

export default function CompareView({ results }) {
  const [expanded, setExpanded] = useState({})

  if (!results || results.length === 0) {
    return <div className="text-center text-gray-400 dark:text-gray-500 py-8">게임을 선택하세요</div>
  }

  const toggleExpand = (gameId) => {
    setExpanded(prev => ({ ...prev, [gameId]: !prev[gameId] }))
  }

  // 가로 누적 막대 차트 데이터 — 게임당 1행
  const sentimentData = results.map(r => {
    const s = r.report?.sentiment || {}
    const name = r.game_name.length > 12 ? r.game_name.slice(0, 12) + '…' : r.game_name
    return {
      name,
      긍정: Math.round((s.positive || 0) * 100),
      중립: Math.round((s.neutral || 0) * 100),
      부정: Math.round((s.negative || 0) * 100),
    }
  })

  const chartHeight = Math.max(results.length * 52 + 60, 160)
  const gridClass = GRID_COLS[Math.min(results.length, 4)]

  return (
    <div className="space-y-6">

      {/* 감성 분포 비교 — 가로 누적 막대 */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="font-semibold mb-1 text-slate-800 dark:text-slate-100">감성 분포 비교</h3>
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">긍정 / 중립 / 부정 비율 (%)을 게임별로 비교합니다.</p>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={sentimentData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barSize={20}>
            <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v, name) => [`${v}%`, name]} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="긍정" stackId="a" fill={S.pos} />
            <Bar dataKey="중립" stackId="a" fill={S.neu} />
            <Bar dataKey="부정" stackId="a" fill={S.neg} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 게임별 카드 */}
      <div className={`grid ${gridClass} gap-4`}>
        {results.map((r, i) => (
          <GameCard
            key={r.game_id}
            r={r}
            color={COLORS[i]}
            isExpanded={!!expanded[r.game_id]}
            onToggle={() => toggleExpand(r.game_id)}
          />
        ))}
      </div>

    </div>
  )
}
