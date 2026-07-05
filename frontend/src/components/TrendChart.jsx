import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { SENTIMENT } from '../colors.js'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg px-4 py-3 text-sm">
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 font-medium">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
          <span className="text-slate-600 dark:text-slate-300">{entry.dataKey}</span>
          <span className="ml-auto font-semibold tabular-nums" style={{ color: entry.color }}>{entry.value}%</span>
        </div>
      ))}
    </div>
  )
}

export default function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[240px] text-slate-400 dark:text-slate-500 text-sm">
        데이터 없음
      </div>
    )
  }

  const chartData = data.map(r => ({
    date: r.report_date,
    긍정: Math.round((r.sentiment?.positive || 0) * 100),
    부정: Math.round((r.sentiment?.negative || 0) * 100),
    중립: Math.round((r.sentiment?.neutral || 0) * 100),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.6} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          unit="%"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          domain={[0, 100]}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          iconType="circle"
          iconSize={8}
        />
        <Line type="monotone" dataKey="긍정" stroke={SENTIMENT.pos} strokeWidth={2.5} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />
        <Line type="monotone" dataKey="중립" stroke={SENTIMENT.neu} strokeWidth={2.5} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />
        <Line type="monotone" dataKey="부정" stroke={SENTIMENT.neg} strokeWidth={2.5} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
