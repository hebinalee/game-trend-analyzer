import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend, ResponsiveContainer, Tooltip
} from 'recharts'

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444']

export default function CompareView({ results }) {
  if (!results || results.length === 0) {
    return <div className="text-center text-gray-400 dark:text-gray-500 py-8">게임을 선택하세요</div>
  }

  const radarData = [
    { subject: '긍정' },
    { subject: '중립' },
    { subject: '부정' },
  ].map(row => {
    const enriched = { ...row }
    results.forEach(r => {
      const s = r.report?.sentiment || {}
      if (row.subject === '긍정') enriched[r.game_name] = Math.round((s.positive || 0) * 100)
      if (row.subject === '중립') enriched[r.game_name] = Math.round((s.neutral || 0) * 100)
      if (row.subject === '부정') enriched[r.game_name] = Math.round((s.negative || 0) * 100)
    })
    return enriched
  })

  return (
    <div className="space-y-6">
      {/* 레이더 차트 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-semibold mb-4 text-center">감성 비교</h3>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="subject" />
            <Tooltip formatter={(v) => `${v}%`} />
            <Legend />
            {results.map((r, i) => (
              <Radar
                key={r.game_id}
                name={r.game_name}
                dataKey={r.game_name}
                stroke={COLORS[i]}
                fill={COLORS[i]}
                fillOpacity={0.15}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* 카드 비교 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {results.map((r, i) => (
          <div
            key={r.game_id}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
            style={{ borderTopColor: COLORS[i], borderTopWidth: 3 }}
          >
            <h4 className="font-semibold mb-2">{r.game_name}</h4>
            {r.report ? (
              <>
                <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 mb-3">
                  {r.report.summary || '요약 없음'}
                </p>
                <div className="flex flex-wrap gap-1">
                  {(r.report.hot_topics || []).slice(0, 3).map((t, j) => (
                    <span key={j} className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                      {t}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-400">데이터 없음</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
