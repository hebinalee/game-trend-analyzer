import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

export default function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-center text-gray-400 dark:text-gray-500 py-8">데이터 없음</div>
  }

  const chartData = data.map(r => ({
    date: r.report_date,
    긍정: Math.round((r.sentiment?.positive || 0) * 100),
    부정: Math.round((r.sentiment?.negative || 0) * 100),
    중립: Math.round((r.sentiment?.neutral || 0) * 100),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
        <YAxis unit="%" tick={{ fontSize: 12 }} domain={[0, 100]} />
        <Tooltip formatter={(v) => `${v}%`} />
        <Legend />
        <Line type="monotone" dataKey="긍정" stroke="#22c55e" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="중립" stroke="#9ca3af" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="부정" stroke="#ef4444" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
