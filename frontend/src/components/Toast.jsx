import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'

// ─── Context ────────────────────────────────────────────────────────────────

const ToastContext = createContext(null)

// ─── Config ─────────────────────────────────────────────────────────────────

const TOAST_DURATION = 3000 // ms

const VARIANTS = {
  success: {
    icon: CheckCircle2,
    borderColor: 'border-l-green-500',
    iconColor: 'text-green-500',
    bg: 'bg-white dark:bg-slate-800',
  },
  error: {
    icon: XCircle,
    borderColor: 'border-l-red-500',
    iconColor: 'text-red-500',
    bg: 'bg-white dark:bg-slate-800',
  },
  info: {
    icon: Info,
    borderColor: 'border-l-indigo-500',
    iconColor: 'text-indigo-500',
    bg: 'bg-white dark:bg-slate-800',
  },
}

// ─── Single Toast item ───────────────────────────────────────────────────────

function ToastItem({ id, message, type = 'info', onDismiss }) {
  const variant = VARIANTS[type] ?? VARIANTS.info
  const Icon = variant.icon

  // Auto-dismiss
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), TOAST_DURATION)
    return () => clearTimeout(timer)
  }, [id, onDismiss])

  return (
    <div
      className={[
        'flex items-start gap-3 w-80 max-w-[calc(100vw-2rem)]',
        'rounded-xl border-l-4 px-4 py-3.5 shadow-xl',
        'toast-enter',
        variant.borderColor,
        variant.bg,
      ].join(' ')}
      role="alert"
    >
      <Icon size={18} strokeWidth={2} className={`mt-0.5 shrink-0 ${variant.iconColor}`} />
      <p className="flex-1 text-sm font-medium text-slate-700 dark:text-slate-200 leading-snug">
        {message}
      </p>
      <button
        onClick={() => onDismiss(id)}
        className="shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
        aria-label="닫기"
      >
        <X size={15} strokeWidth={2} />
      </button>
    </div>
  )
}

// ─── Provider ────────────────────────────────────────────────────────────────

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const counterRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback(({ message, type = 'info' }) => {
    const id = ++counterRef.current
    setToasts(prev => [...prev, { id, message, type }])
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast portal — fixed top-right */}
      <div
        className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 items-end pointer-events-none"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem {...t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
