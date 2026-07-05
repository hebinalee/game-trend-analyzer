import { Check } from 'lucide-react'

export default function GameSelector({ games, selected, onChange, max = 4 }) {
  const toggle = (id) => {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id))
    } else if (selected.length < max) {
      onChange([...selected, id])
    }
  }

  return (
    <div className="space-y-2">
      {selected.length > 0 && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 rounded-full font-medium">
            {selected.length}개 선택됨
          </span>
          <span className="ml-2">최대 {max}개까지 선택 가능</span>
        </p>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
        {games.map(game => {
          const checked = selected.includes(game.id)
          const disabled = !checked && selected.length >= max
          return (
            <label
              key={game.id}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-all select-none
                ${checked
                  ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-400 dark:border-indigo-600 text-indigo-700 dark:text-indigo-300 shadow-sm'
                  : disabled
                    ? 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-400 dark:text-slate-600 cursor-not-allowed opacity-60'
                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/10'
                }`}
            >
              <input
                type="checkbox"
                className="sr-only"
                checked={checked}
                disabled={disabled}
                onChange={() => toggle(game.id)}
              />
              <span
                className={`w-4 h-4 rounded shrink-0 flex items-center justify-center border transition-colors ${
                  checked
                    ? 'bg-indigo-600 border-indigo-600'
                    : disabled
                      ? 'border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-700'
                      : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700'
                }`}
              >
                {checked && <Check size={10} strokeWidth={3} className="text-white" />}
              </span>
              <span className="truncate leading-tight">{game.name}</span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
