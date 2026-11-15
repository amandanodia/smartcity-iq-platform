import { useEffect, useState } from 'react'
import { ArrowUpRight, BookOpen, FileSpreadsheet } from 'lucide-react'
import { EmptyPanel, ErrorPanel, LoadingPanel } from '../components/StatePanel'
import { api } from '../services/api'
import type { DataSource } from '../types/api'

export function DataSourcesPage() {
  const [sources, setSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    api.dataSources().then(({ data }) => { if (active) setSources(data) }).catch((reason: Error) => { if (active) setError(reason.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  return <div className="space-y-5"><section><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-800">Provenance registry</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Data sources</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Providers are registered separately so dataset-specific access, licensing, attribution, and coverage can be tracked.</p></section>
    {loading ? <LoadingPanel label="Loading registered sources" /> : error ? <ErrorPanel message={error} /> : sources.length === 0 ? <EmptyPanel title="No source records registered">Run the source seed script or register sources in the database. No source availability is assumed here.</EmptyPanel> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{sources.map((source) => <article key={source.id} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.02]"><div className="flex items-start justify-between gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-blue-50 text-blue-800"><BookOpen className="h-5 w-5" /></span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium capitalize text-slate-600">{source.access_method.replaceAll('_', ' ')}</span></div><h3 className="mt-4 text-base font-semibold text-slate-900">{source.name}</h3><div className="mt-3 space-y-2 text-sm">{source.license ? <p className="text-slate-600"><span className="font-medium text-slate-800">License:</span> {source.license}{source.license_url && <> · <a href={source.license_url} target="_blank" rel="noreferrer" className="text-blue-800 hover:underline">terms</a></>}</p> : <p className="text-slate-500">License: check the specific dataset resource</p>}{source.attribution && <p className="text-xs text-slate-500">Attribution: {source.attribution}</p>}</div><div className="mt-auto flex flex-wrap gap-2 pt-5">{source.base_url && <a href={source.base_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Visit source <ArrowUpRight className="h-3.5 w-3.5" /></a>}<span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500"><FileSpreadsheet className="h-3.5 w-3.5" />Dataset-specific coverage</span></div></article>)}</div>}
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><strong>Availability varies.</strong> A registered provider does not mean every city or domain has usable observations. Check dataset coverage, reporting dates, and source terms before interpreting results. API credentials are not displayed in this view.</div>
  </div>
}
