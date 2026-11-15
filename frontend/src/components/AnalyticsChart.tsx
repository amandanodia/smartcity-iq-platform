import { Bar } from 'react-chartjs-2'
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import type { AnalyticsRow } from '../types/api'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const palette = ['#174a7e', '#2c7fb8', '#41b6c4', '#7fcdbb', '#f0a64b', '#8b78b7', '#dd6b61', '#5a8f70']

export function AnalyticsChart({ rows, title, unit }: { rows: AnalyticsRow[]; title: string; unit: string }) {
  const ordered = [...rows].sort((a, b) => (a.city ?? '').localeCompare(b.city ?? '') || (a.coverage.area ?? '').localeCompare(b.coverage.area ?? ''))
  const labels = ordered.map((row) => `${row.city ?? 'City not assigned'}${row.coverage.area ? ` · ${row.coverage.area}` : ''}`)
  const chartData = {
    labels,
    datasets: [{ label: `Mean (${unit})`, data: ordered.map((row) => row.mean),
      backgroundColor: ordered.map((_, index) => palette[index % palette.length]), borderRadius: 5, maxBarThickness: 42 }],
  }
  return <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="mb-4"><h3 className="font-semibold text-slate-900">{title}</h3><p className="mt-1 text-xs text-slate-500">Mean normalized value by reported location · {unit} · {ordered.reduce((sum, row) => sum + row.observation_count, 0).toLocaleString('en-IN')} observations</p></div><div className="h-[300px] w-full"><Bar data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => `${Number(context.parsed.y).toLocaleString('en-IN', { maximumFractionDigits: 2 })} ${unit}` } } }, scales: { x: { grid: { display: false }, ticks: { color: '#64748b', maxRotation: 35, minRotation: 0 } }, y: { beginAtZero: false, title: { display: true, text: unit }, ticks: { color: '#64748b' }, grid: { color: '#e8edf2' } } } }} aria-label={`${title}, mean normalized value in ${unit}`} role="img" /></div></section>
}
