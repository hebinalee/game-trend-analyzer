import { useEffect, useState } from 'react'
import { getGames, compareGames } from '../api.js'
import GameSelector from '../components/GameSelector.jsx'
import CompareView from '../components/CompareView.jsx'

const PLATFORM_FILTERS = [
  { key: 'all',    label: '전체' },
  { key: 'steam',  label: 'PC (Steam)' },
  { key: 'mobile', label: '모바일' },
]

export default function Compare() {
  const [games, setGames] = useState([])
  const [gamesError, setGamesError] = useState(false)
  const [selected, setSelected] = useState([])
  const [platformFilter, setPlatformFilter] = useState('all')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getGames()
      .then(setGames)
      .catch(() => setGamesError(true))
  }, [])

  const filteredGames = platformFilter === 'all'
    ? games
    : games.filter(g => g.platform === platformFilter)

  const handlePlatformChange = (key) => {
    setPlatformFilter(key)
    setSelected([])
    setResults([])
  }

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

        {/* 플랫폼 필터 */}
        <div className="flex gap-2 mb-4">
          {PLATFORM_FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handlePlatformChange(key)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                platformFilter === key
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-indigo-400'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {gamesError ? (
          <p className="text-sm text-red-500">게임 목록을 불러오지 못했습니다. 백엔드 연결을 확인해주세요.</p>
        ) : filteredGames.length === 0 && games.length > 0 ? (
          <p className="text-sm text-gray-400">선택한 플랫폼에 해당하는 게임이 없습니다.</p>
        ) : (
          <GameSelector games={filteredGames} selected={selected} onChange={setSelected} max={4} />
        )}
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
