import { useEffect, useState } from 'react'
import { getGames, compareGames } from '../api.js'
import GameSelector from '../components/GameSelector.jsx'
import CompareView from '../components/CompareView.jsx'

export default function Compare() {
  const [games, setGames] = useState([])
  const [selected, setSelected] = useState([])
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getGames().then(setGames).catch(() => {})
  }, [])

  const handleCompare = () => {
    if (selected.length < 2) {
      alert('2개 이상 게임을 선택하세요.')
      return
    }
    setLoading(true)
    setError(null)
    compareGames(selected, date)
      .then(setResults)
      .catch(() => setError('비교 데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">게임 비교</h1>

      {/* 게임 선택 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">게임 선택 (최대 4개)</h2>
          <div className="flex items-center gap-3">
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
            />
            <button
              onClick={handleCompare}
              disabled={selected.length < 2}
              className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              비교하기
            </button>
          </div>
        </div>
        <GameSelector games={games} selected={selected} onChange={setSelected} max={4} />
      </div>

      {/* 결과 */}
      {error && (
        <div className="text-red-500 text-sm">{error}</div>
      )}
      {loading ? (
        <div className="text-center py-12 text-gray-400">분석 중...</div>
      ) : (
        <CompareView results={results} />
      )}
    </div>
  )
}
