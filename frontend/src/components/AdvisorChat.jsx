import { useState, useRef, useEffect } from 'react'
import { Bot, Send, Wrench, Loader2 } from 'lucide-react'
import { askLiveOpsAdvisor } from '../api.js'

const TOOL_LABEL = {
  get_recent_reviews: '최근 리뷰 조회',
  get_patch_notes: '패치노트 조회',
  get_sentiment_stats: '감성 통계 분석',
  search_by_keyword: '키워드 검색',
}

const SUGGESTIONS = [
  '최근 7일 유저 반응은 어떤가요?',
  '부정적인 리뷰에서 가장 많이 언급된 문제는?',
  '최근 패치 이후 감성이 어떻게 변했나요?',
  '운영자가 즉시 대응해야 할 이슈가 있나요?',
]

function ToolBadge({ name }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded-full bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300">
      <Wrench size={10} strokeWidth={2.5} />
      {TOOL_LABEL[name] ?? name}
    </span>
  )
}

function formatTime(date) {
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function Message({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end gap-2">
        <div className="flex flex-col items-end gap-1">
          <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
            {msg.content}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-slate-500 px-1">
            {formatTime(msg.timestamp)}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start gap-2">
      <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0 mt-0.5">
        <Bot size={14} className="text-indigo-600 dark:text-indigo-400" />
      </div>
      <div className="max-w-[80%] space-y-1.5">
        <div className="bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
        {msg.tools_used?.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1">
            {msg.tools_used.map((t, i) => <ToolBadge key={i} name={t} />)}
          </div>
        )}
        <span className="text-[10px] text-slate-400 dark:text-slate-500 px-1 block">
          {formatTime(msg.timestamp)}
        </span>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start gap-2">
      <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0">
        <Bot size={14} className="text-indigo-600 dark:text-indigo-400" />
      </div>
      <div className="bg-slate-100 dark:bg-slate-700 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1.5 items-center h-4">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}

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
    setMessages(prev => [...prev, { role: 'user', content: q, timestamp: new Date() }])
    setLoading(true)
    try {
      const res = await askLiveOpsAdvisor(gameId, q)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        tools_used: res.tools_used,
        timestamp: new Date(),
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '답변을 가져오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.',
        tools_used: [],
        timestamp: new Date(),
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
    <div className="flex flex-col h-[calc(100vh-240px)] min-h-[520px]">
      {/* 헤더 */}
      <div className="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700 mb-4 shrink-0">
        <div className="w-9 h-9 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
          <Bot size={18} className="text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">AI LiveOps Advisor</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">{gameName} 데이터를 기반으로 운영 인사이트를 제공합니다</p>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4">
            <div>
              <div className="w-14 h-14 rounded-2xl bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center mx-auto mb-3">
                <Bot size={28} className="text-indigo-600 dark:text-indigo-400" />
              </div>
              <p className="text-base font-semibold text-slate-700 dark:text-slate-200 mb-1">
                무엇이 궁금하신가요?
              </p>
              <p className="text-sm text-slate-400 dark:text-slate-500">
                아래 질문을 선택하거나 직접 입력해보세요
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left px-4 py-3 text-sm rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:border-indigo-300 dark:hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-all leading-snug"
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
      <div className="pt-3 border-t border-slate-200 dark:border-slate-700 shrink-0">
        <div className="flex gap-2 items-end bg-slate-50 dark:bg-slate-700 rounded-2xl border border-slate-200 dark:border-slate-600 px-3 py-2 focus-within:border-indigo-400 dark:focus-within:border-indigo-500 transition-colors">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={`${gameName}에 대해 질문하세요...`}
            disabled={loading}
            className="flex-1 resize-none bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none disabled:opacity-50 leading-relaxed py-0.5"
            style={{ maxHeight: '120px' }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="w-8 h-8 flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0 self-end"
          >
            {loading
              ? <Loader2 size={15} className="animate-spin" />
              : <Send size={15} strokeWidth={2.5} />
            }
          </button>
        </div>
        <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1.5 ml-1">
          Enter로 전송 · Shift+Enter로 줄바꿈
        </p>
      </div>
    </div>
  )
}
