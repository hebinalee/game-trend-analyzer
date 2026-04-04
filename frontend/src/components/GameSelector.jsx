export default function GameSelector({ games, selected, onChange, max = 4 }) {
  const toggle = (id) => {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id))
    } else if (selected.length < max) {
      onChange([...selected, id])
    }
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
      {games.map(game => {
        const checked = selected.includes(game.id)
        const disabled = !checked && selected.length >= max
        return (
          <label
            key={game.id}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors
              ${checked
                ? 'bg-indigo-100 dark:bg-indigo-900 border-indigo-400 text-indigo-700 dark:text-indigo-300'
                : disabled
                  ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-indigo-300'
              }`}
          >
            <input
              type="checkbox"
              className="sr-only"
              checked={checked}
              disabled={disabled}
              onChange={() => toggle(game.id)}
            />
            <span>{game.name}</span>
          </label>
        )
      })}
    </div>
  )
}
