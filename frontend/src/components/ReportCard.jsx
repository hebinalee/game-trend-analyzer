export default function ReportCard({ game, report, onClick }) {
  const sentiment = report?.sentiment || {}
  const pos = Math.round((sentiment.positive || 0) * 100)
  const neg = Math.round((sentiment.negative || 0) * 100)
  const neu = 100 - pos - neg

  return (
    <div
      onClick={onClick}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 cursor-pointer hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-500 transition-all"
    >
      <div className="flex items-center gap-3 mb-3">
        {game.thumbnail_url ? (
          <img
            src={game.thumbnail_url}
            alt={game.name}
            className="w-10 h-10 rounded-lg object-cover bg-gray-100"
            onError={e => { e.target.style.display = 'none' }}
          />
        ) : (
          <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold text-sm">
            {game.name.slice(0, 2)}
          </div>
        )}
        <h3 className="font-semibold text-base">{game.name}</h3>
      </div>

      {report ? (
        <>
          {/* 감성 바 */}
          <div className="flex h-2 rounded-full overflow-hidden mb-3">
            <div className="bg-green-400" style={{ width: `${pos}%` }} title={`긍정 ${pos}%`} />
            <div className="bg-gray-300 dark:bg-gray-600" style={{ width: `${neu}%` }} title={`중립 ${neu}%`} />
            <div className="bg-red-400" style={{ width: `${neg}%` }} title={`부정 ${neg}%`} />
          </div>
          <div className="flex gap-2 text-xs text-gray-500 dark:text-gray-400 mb-3">
            <span className="text-green-500">긍정 {pos}%</span>
            <span>중립 {neu}%</span>
            <span className="text-red-500">부정 {neg}%</span>
          </div>

          {/* 요약 */}
          <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 mb-3">
            {report.summary || '요약 없음'}
          </p>

          {/* 핫토픽 태그 */}
          <div className="flex flex-wrap gap-1">
            {(report.hot_topics || []).slice(0, 3).map((topic, i) => (
              <span key={i} className="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 text-xs rounded-full">
                {topic}
              </span>
            ))}
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-400 dark:text-gray-500">데이터 없음</p>
      )}
    </div>
  )
}
