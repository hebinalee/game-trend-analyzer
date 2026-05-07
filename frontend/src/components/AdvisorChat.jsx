import { useState, useRef, useEffect } from 'react'
import { askLiveOpsAdvisor } from '../api.js'

const TOOL_LABEL = {
  get_recent_reviews: '최근 리뷰 조회',
  get_patch_notes: '패치노트 조회',
  get_sentiment_stats: '감성 통계 분석',
  search_by_keyword: '키워드 검색',
}

function ToolBadge({ name }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300">
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 dark:bg-indigo-500 inline-block" />
      {TOOL_LABEL[name] ?? name}
    </span>
  )
}

function Message({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] space-y-2">
        <div className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
          {msg.content}
        </div>
        {msg.tools_used?.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1">
            {msg.tools_used.map((t, i) => <ToolBadge key={i} name={t} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  '최근 7일 유저 반응은 어떤가요?',
  '부정적인 리뷰에서 가장 많이 언급된 문제는?',
  '최근 패치 이후 감성이 어떻게 변했나요?',
  '운영자가 즉시 대응해야 할 이슈가 있나요?',
]

export default function AdvisorChat({ gameId, gameName }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (question) => {
    const q = question ?? input.trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await askLiveOpsAdvisor(gameId, q)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        tools_used: res.tools_used,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '답변을 가져오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.',
        tools_used: [],
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-[calc(100vh-240px)] min-h-[480px]">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-1">
                {gameName} AI 어드바이저
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Steam 리뷰와 패치노트를 분석하여 운영 인사이트를 제공합니다
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left px-4 py-3 text-sm rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => <Message key={i} msg={msg} />)}
            {loading && <TypingIndicator />}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력 영역 */}
      <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={`${gameName}에 대해 질문하세요...`}
            disabled={loading}
            className="flex-1 resize-none px-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 leading-relaxed"
            style={{ maxHeight: '120px' }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm font-medium flex-shrink-0"
          >
            전송
          </button>
        </div>
        <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-1.5 ml-1">
          Enter로 전송 · Shift+Enter로 줄바꿈
        </p>
      </div>
    </div>
  )
}
