import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getGames, getReports, getLatestReport } from '../api.js'
import TrendChart from '../components/TrendChart.jsx'

function IssueSection({ title, items, color }) {
  if (!items || items.length === 0) return null
  return (
    <div className="mb-3">
      <h5 className={`text-xs font-semibold uppercase tracking-wide mb-1 ${color}`}>{title}</h5>
      <div className="flex flex-wrap gap-1">
        {items.map((item, i) => (
          <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded-full text-gray-700 dark:text-gray-300">
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function GameDetail() {
  const { id } = useParams()
  const gameId = parseInt(id)
  const [game, setGame] = useState(null)
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      getGames(),
      getLatestReport(gameId).catch(() => null),
      getReports(gameId),
    ]).then(([games, latest, hist]) => {
      setGame(games.find(g => g.id === gameId) || null)
      setReport(latest)
      setHistory(hist)
    }).catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [gameId])

  if (loading) return <div className="text-center py-20 text-gray-400">로딩 중...</div>
  if (error) return <div className="text-center py-20 text-red-500">{error}</div>

  const sentiment = report?.sentiment || {}
  const pos = Math.round((sentiment.positive || 0) * 100)
  const neg = Math.round((sentiment.negative || 0) * 100)
  const neu = 100 - pos - neg

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* 좌측 사이드바 */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 sticky top-4">
          <div className="w-16 h-16 rounded-xl bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold text-xl mb-3">
            {game?.name.slice(0, 2)}
          </div>
          <h2 className="font-bold text-lg mb-4">{game?.name}</h2>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">날짜 선택</label>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          {report && (
            <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
              게시글 수: {report.raw_post_count}개
            </div>
          )}
        </div>
      </div>

      {/* 우측 콘텐츠 */}
      <div className="lg:col-span-3 space-y-6">
        {/* 최신 리포트 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-lg mb-4">오늘의 리포트</h3>
          {report ? (
            <>
              <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-4">
                {report.summary}
              </p>

              {/* 감성 */}
              <div className="mb-4">
                <div className="flex h-3 rounded-full overflow-hidden mb-1">
                  <div className="bg-green-400" style={{ width: `${pos}%` }} />
                  <div className="bg-gray-300 dark:bg-gray-600" style={{ width: `${neu}%` }} />
                  <div className="bg-red-400" style={{ width: `${neg}%` }} />
                </div>
                <div className="flex gap-3 text-xs text-gray-500 dark:text-gray-400">
                  <span className="text-green-500">긍정 {pos}%</span>
                  <span>중립 {neu}%</span>
                  <span className="text-red-500">부정 {neg}%</span>
                </div>
              </div>

              {/* 이슈 */}
              <IssueSection title="버그" items={report.key_issues?.bugs} color="text-red-500" />
              <IssueSection title="요청사항" items={report.key_issues?.requests} color="text-blue-500" />
              <IssueSection title="운영이슈" items={report.key_issues?.operations} color="text-orange-500" />

              {/* 키워드 */}
              {report.trend_keywords?.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">트렌드 키워드</h5>
                  <div className="flex flex-wrap gap-1">
                    {report.trend_keywords.slice(0, 10).map((kw, i) => (
                      <span key={i} className="px-2 py-0.5 text-xs bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded-full">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-gray-400 dark:text-gray-500">리포트가 없습니다.</p>
          )}
        </div>

        {/* 감성 추이 차트 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-lg mb-4">최근 7일 감성 추이</h3>
          <TrendChart data={history} />
        </div>
      </div>
    </div>
  )
}
