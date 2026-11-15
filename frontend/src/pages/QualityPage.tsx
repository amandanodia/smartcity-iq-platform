import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, ClipboardCheck } from 'lucide-react'
import { EmptyPanel, ErrorPanel, LoadingPanel } from '../components/StatePanel'
import { api } from '../services/api'
import type { QualityReport } from '../types/api'

export function QualityPage() {
  const [reports, setReports] = useState<QualityReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    api.quality().then(({ data }) => { if (active) setReports(data) }).catch((reason: Error) => { if (active) setError(reason.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  return <div className="space-y-5"><section><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-800">Validation record</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Data quality</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Import reports record missing cells, duplicate rows, and row-level processing warnings. Raw input remains available for audit.</p></section>
    {loading ? <LoadingPanel label="Loading quality reports" /> : error ? <ErrorPanel message={error} /> : reports.length === 0 ? <EmptyPanel title="No quality reports yet">Quality summaries appear after a CSV or Excel file has been imported.</EmptyPanel> : <div className="space-y-3">{reports.map((report) => { const warnings = report.warnings ?? []; const missingTotal = Object.values(report.missing_value_counts ?? {}).reduce((sum, value) => sum + value, 0); const hasWarnings = warnings.length > 0 || report.duplicate_rows > 0 || missingTotal > 0; return <article key={report.id} className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div className="flex gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${hasWarnings ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>{hasWarnings ? <AlertTriangle className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}</span><div><h3 className="font-semibold text-slate-900">Dataset {report.dataset_id}{report.import_batch_id ? ` · Import batch ${report.import_batch_id}` : ''}</h3><p className="mt-1 text-xs text-slate-500">Report generated {new Date(report.generated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</p></div></div><div className="flex gap-5 text-sm"><div><p className="text-xs text-slate-500">Rows checked</p><p className="mt-1 font-semibold tabular-nums">{report.rows_checked.toLocaleString('en-IN')}</p></div><div><p className="text-xs text-slate-500">Duplicates</p><p className="mt-1 font-semibold tabular-nums">{report.duplicate_rows.toLocaleString('en-IN')}</p></div><div><p className="text-xs text-slate-500">Missing cells</p><p className="mt-1 font-semibold tabular-nums">{missingTotal.toLocaleString('en-IN')}</p></div></div></div>
      {Object.keys(report.missing_value_counts ?? {}).length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Missing values by source column</p><div className="flex flex-wrap gap-2">{Object.entries(report.missing_value_counts).filter(([, count]) => count > 0).map(([column, count]) => <span key={column} className="rounded-full bg-amber-50 px-3 py-1.5 text-xs text-amber-900">{column}: {count.toLocaleString('en-IN')}</span>)}{missingTotal === 0 && <span className="text-xs text-slate-500">No missing cells were detected.</span>}</div></div>}
      {warnings.length > 0 && <ul className="mt-4 space-y-2 border-t border-slate-100 pt-3">{warnings.map((warning, index) => <li key={`${report.id}-${index}`} className="flex gap-2 text-sm leading-5 text-amber-900"><ClipboardCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />{warning}</li>)}</ul>}</article>})}</div>}
  </div>
}
