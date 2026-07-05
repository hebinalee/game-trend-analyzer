import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  BarChart2, MessageSquare, Bot,
  FileBarChart, TrendingUp, GitCompare,
  Bug, Star, Settings, Calendar, Loader2,
  Monitor, Smartphone, FileText,
  ThumbsUp, Inbox, MessageCircle,
} from 'lucide-react'
import { SENTIMENT } from '../colors.js'
import { getGames, getReports, getLatestReport, compareGames, getPosts } from '../api.js'
import TrendChart from '../components/TrendChart.jsx'
import CompareView from '../components/CompareView.jsx'
import GameSelector from '../components/GameSelector.jsx'
import AdvisorChat from '../components/AdvisorChat.jsx'

// ── 이슈 섹션 ─────────────────────────────────────────────────────────────────

function IssueSection({ icon: Icon, title, items, colorClass, bgClass }) {
  if (!items || items.length === 0) return null
  return (
    <div className="mb-4">
      <h5 className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide mb-2 ${colorClass}`}>
        <Icon size={12} strokeWidth={2.5} />
        {title}
      </h5>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className={`px-2.5 py-1 text-xs rounded-full ${bgClass}`}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── 탭1: 리포트 ────────────────────────────────────────────────────────────────

function ReportTab({ game, report, history, allGames }) {
  const sentiment = report?.sentiment || {}
  const pos = Math.round((sentiment.positive || 0) * 100)
  const neg = Math.round((sentiment.negative || 0) * 100)
  const neu = 100 - pos - neg

  const [compareSelected, setCompareSelected] = useState([])
  const [compareDate, setCompareDate] = useState(new Date().toISOString().split('T')[0])
  const [compareResults, setCompareResults] = useState([])
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState(null)

  const otherGames = allGames.filter(g => g.id !== game?.id)

  const handleCompare = () => {
    if (!game || compareSelected.length === 0) return
    setCompareLoading(true)
    setCompareError(null)
    const ids = [game.id, ...compareSelected]
    compareGames(ids, compareDate)
      .then(setCompareResults)
      .catch(() => setCompareError('비교 데이터를 불러오지 못했습니다.'))
      .finally(() => setCompareLoading(false))
  }

  return (
    <div className="space-y-5">
      {/* 오늘의 리포트 */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
            <FileBarChart size={16} className="text-indigo-600 dark:text-indigo-400" />
          </div>
          <h3 className="font-semibold text-base text-slate-800 dark:text-slate-100">오늘의 리포트</h3>
        </div>

        {report ? (
          <>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300 mb-5">
              {report.summary}
            </p>

            {/* 감성 분포 */}
            <div className="mb-5">
              <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">감성 분포</h5>
              <div className="h-3 flex rounded-full overflow-hidden mb-2.5">
                <div style={{ width: `${pos}%`, backgroundColor: SENTIMENT.pos }} />
                <div style={{ width: `${neu}%`, backgroundColor: SENTIMENT.neu }} />
                <div style={{ width: `${neg}%`, backgroundColor: SENTIMENT.neg }} />
              </div>
              <div className="flex gap-3 flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400">
                  <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
                  긍정 {pos}%
                </span>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
                  <span className="w-2 h-2 rounded-full bg-slate-400 shrink-0" />
                  중립 {neu}%
                </span>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
                  <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
                  부정 {neg}%
                </span>
              </div>
            </div>

            <IssueSection
              icon={Bug}
              title="버그"
              items={report.key_issues?.bugs}
              colorClass="text-red-500"
              bgClass="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
            />
            <IssueSection
              icon={Star}
              title="요청사항"
              items={report.key_issues?.requests}
              colorClass="text-blue-500"
              bgClass="bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400"
            />
            <IssueSection
              icon={Settings}
              title="운영이슈"
              items={report.key_issues?.operations}
              colorClass="text-orange-500"
              bgClass="bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400"
            />

            {report.trend_keywords?.length > 0 && (
              <div>
                <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">트렌드 키워드</h5>
                <div className="flex flex-wrap gap-1.5">
                  {report.trend_keywords.slice(0, 10).map((kw, i) => (
                    <span key={i} className="px-2.5 py-1 text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full border border-indigo-100 dark:border-indigo-800">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-slate-400 dark:text-slate-500">
            <FileBarChart size={32} className="mb-2 opacity-40" />
            <p className="text-sm">리포트가 없습니다.</p>
          </div>
        )}
      </div>

      {/* 감성 추이 차트 */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
            <TrendingUp size={16} className="text-emerald-600 dark:text-emerald-400" />
          </div>
          <h3 className="font-semibold text-base text-slate-800 dark:text-slate-100">최근 7일 감성 추이</h3>
        </div>
        <TrendChart data={history} />
      </div>

      {/* 경쟁작 비교 */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center">
              <GitCompare size={16} className="text-violet-600 dark:text-violet-400" />
            </div>
            <h3 className="font-semibold text-base text-slate-800 dark:text-slate-100">경쟁작 비교</h3>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex items-center">
              <Calendar size={14} className="absolute left-2.5 text-slate-400 pointer-events-none" />
              <input
                type="date"
                value={compareDate}
                onChange={e => setCompareDate(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-colors"
              />
            </div>
            <button
              onClick={handleCompare}
              disabled={compareSelected.length === 0 || compareLoading}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all font-medium"
            >
              {compareLoading
                ? <><Loader2 size={14} className="animate-spin" /> 분석 중...</>
                : <><GitCompare size={14} /> 비교하기</>
              }
            </button>
          </div>
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-4 ml-10">
          비교할 게임을 선택하세요. 현재 게임({game?.name})은 자동으로 포함됩니다.
        </p>
        <GameSelector games={otherGames} selected={compareSelected} onChange={setCompareSelected} max={3} />
        {compareError && (
          <p className="mt-3 text-sm text-red-500 dark:text-red-400">{compareError}</p>
        )}
        {compareResults.length > 0 && (
          <div className="mt-5">
            <CompareView results={compareResults} />
          </div>
        )}
      </div>
    </div>
  )
}

// ── 탭2: 최근 게시글 ───────────────────────────────────────────────────────────

const SOURCE_META = {
  steam_review: { label: 'Steam', Icon: Monitor, className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  steam_news: { label: 'Steam 뉴스', Icon: Monitor, className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  reddit: { label: 'Reddit', Icon: MessageCircle, className: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' },
  google_play: { label: 'Google Play', Icon: Smartphone, className: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
  app_store: { label: 'App Store', Icon: Smartphone, className: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300' },
}

// Fallback: match by prefix
function getSourceMeta(source) {
  if (!source) return null
  if (SOURCE_META[source]) return SOURCE_META[source]
  if (source.startsWith('steam')) return SOURCE_META.steam_review
  if (source.startsWith('reddit')) return SOURCE_META.reddit
  if (source.startsWith('google')) return SOURCE_META.google_play
  if (source.startsWith('app')) return SOURCE_META.app_store
  return null
}

const TYPE_LABELS = {
  review: '리뷰',
  news: '공지',
  community: '커뮤니티',
}

const SELECT_CLASS =
  'px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-colors'

function PostsTab({ game }) {
  const [posts, setPosts] = useState([])
  const [source, setSource] = useState('')
  const [daysBack, setDaysBack] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = () => {
    if (!game) return
    setLoading(true)
    setError(null)
    getPosts(game.id, { source: source || undefined, daysBack })
      .then(setPosts)
      .catch(() => setError('게시글을 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { if (game) load() }, [game])

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
      {/* 필터 바 */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <h3 className="font-semibold text-base text-slate-800 dark:text-slate-100 mr-1">최근 수집 게시글</h3>
        <div className="flex items-center gap-2 ml-auto">
          <select
            value={source}
            onChange={e => setSource(e.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">전체 플랫폼</option>
            <option value="steam_review">Steam</option>
            <option value="reddit">Reddit</option>
            <option value="google_play">Google Play</option>
            <option value="app_store">App Store</option>
          </select>
          <select
            value={daysBack}
            onChange={e => setDaysBack(Number(e.target.value))}
            className={SELECT_CLASS}
          >
            <option value={1}>최근 1일</option>
            <option value={3}>최근 3일</option>
            <option value={7}>최근 7일</option>
          </select>
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-all font-medium"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : null}
            조회
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-500 dark:text-red-400 mb-4">{error}</p>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="animate-pulse h-20 bg-slate-100 dark:bg-slate-700 rounded-xl" />
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-14 text-slate-400 dark:text-slate-500">
          <Inbox size={36} className="mb-3 opacity-40" />
          <p className="text-sm font-medium">수집된 게시글이 없습니다</p>
          <p className="text-xs mt-1 opacity-70">크롤링을 실행해 보세요.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {posts.map(post => {
            const meta = getSourceMeta(post.source)
            const SourceIcon = meta?.Icon
            return (
              <div
                key={post.id}
                className="flex flex-col gap-2 p-3.5 rounded-xl border border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
              >
                {/* 상단: 배지 + 제목 */}
                <div className="flex items-start gap-2 flex-wrap">
                  {meta && (
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full shrink-0 ${meta.className}`}>
                      {SourceIcon && <SourceIcon size={10} strokeWidth={2.5} />}
                      {meta.label}
                    </span>
                  )}
                  {post.post_type && (
                    <span className="px-2 py-0.5 text-[11px] font-medium rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 shrink-0">
                      {TYPE_LABELS[post.post_type] || post.post_type}
                    </span>
                  )}
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 leading-snug">
                    {post.title || '(제목 없음)'}
                  </span>
                </div>

                {/* 본문 미리보기 */}
                {post.content && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                    {post.content}
                  </p>
                )}

                {/* 하단: 메타 정보 */}
                <div className="flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <ThumbsUp size={11} />
                    {post.like_count ?? 0}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MessageSquare size={11} />
                    {post.comment_count ?? 0}
                  </span>
                  {post.author && <span>by {post.author}</span>}
                  {post.posted_at && (
                    <span className="ml-auto">
                      {new Date(post.posted_at).toLocaleDateString('ko-KR')}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── 탭3: AI 어드바이저 ─────────────────────────────────────────────────────────

function AdvisorTab({ game }) {
  if (!game) return null
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
      <AdvisorChat gameId={game.id} gameName={game.name} />
    </div>
  )
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'report', label: '리포트', Icon: BarChart2 },
  { id: 'posts', label: '최근 게시글', Icon: MessageSquare },
  { id: 'advisor', label: 'AI 어드바이저', Icon: Bot },
]

export default function GameDetail() {
  const { id } = useParams()
  const gameId = parseInt(id)
  const [game, setGame] = useState(null)
  const [allGames, setAllGames] = useState([])
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('report')

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      getGames(),
      getLatestReport(gameId).catch(() => null),
      getReports(gameId),
    ]).then(([games, latest, hist]) => {
      setAllGames(games)
      setGame(games.find(g => g.id === gameId) || null)
      setReport(latest)
      setHistory(hist)
    }).catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [gameId])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3 text-slate-400 dark:text-slate-500">
        <Loader2 size={32} className="animate-spin text-indigo-400" />
        <p className="text-sm">불러오는 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-2 text-red-400">
        <p className="text-sm font-medium">{error}</p>
      </div>
    )
  }

  const PlatformIcon = game?.platform === 'steam' ? Monitor : Smartphone

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* 좌측 사이드바 */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5 sticky top-4">
          {/* 게임 썸네일 */}
          <div className="w-20 h-20 rounded-2xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold text-2xl mb-4 select-none">
            {game?.name.slice(0, 2)}
          </div>

          {/* 게임 이름 */}
          <h2 className="font-bold text-xl text-slate-800 dark:text-slate-100 mb-2 leading-tight">
            {game?.name}
          </h2>

          {/* 플랫폼 배지 */}
          <div className="mb-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
              <PlatformIcon size={12} strokeWidth={2} />
              {game?.platform === 'steam' ? 'Steam (PC)' : 'Mobile'}
            </span>
          </div>

          {/* 통계 */}
          {report && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mb-5">
              <FileText size={12} />
              <span>게시글 {report.raw_post_count}개</span>
              {report.report_date && (
                <>
                  <span className="text-slate-300 dark:text-slate-600">·</span>
                  <span>{report.report_date}</span>
                </>
              )}
            </div>
          )}

          {/* 탭 네비게이션 */}
          <nav className="space-y-0.5">
            {TABS.map(tab => {
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 border-l-2 border-indigo-600 dark:border-indigo-400 pl-[10px]'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <tab.Icon size={16} strokeWidth={2} />
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      {/* 우측 콘텐츠 */}
      <div className="lg:col-span-3">
        {activeTab === 'report' && (
          <ReportTab game={game} report={report} history={history} allGames={allGames} />
        )}
        {activeTab === 'posts' && (
          <PostsTab game={game} />
        )}
        {activeTab === 'advisor' && (
          <AdvisorTab game={game} />
        )}
      </div>
    </div>
  )
}
