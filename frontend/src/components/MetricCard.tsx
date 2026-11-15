import type { LucideIcon } from 'lucide-react'

export function MetricCard({ label, value, detail, icon: Icon }: { label: string; value: string | number; detail: string; icon: LucideIcon }) {
  return <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.02]"><div className="flex items-start justify-between"><p className="text-sm font-medium text-slate-500">{label}</p><span className="rounded-lg bg-blue-50 p-2 text-blue-800"><Icon className="h-4 w-4" /></span></div><p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{value}</p><p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p></article>
}
