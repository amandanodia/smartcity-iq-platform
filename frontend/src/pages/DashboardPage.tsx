import { useEffect, useState } from 'react'
import { Activity, Database, Layers3, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useFilters } from '../app/FilterContext'
import { MetricCard } from '../components/MetricCard'
import { EmptyPanel, ErrorPanel, LoadingPanel } from '../components/StatePanel'
import { api } from '../services/api'
import type { Coverage, Dataset, QualityReport } from '../types/api'

interface DashboardData { datasets: Dataset[]; datasetTotal: number; coverage: Coverage[]; coverageCapped: boolean; quality: QualityReport[]; airCount: number; safetyCount: number; airCapped: boolean; safetyCapped: boolean }

export function DashboardPage() {
  const filters = useFilters()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const selectedCity = filters.cities.find((city) => String(city.id) === filters.cityId)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    const params = filters.analyticsParams()
    Promise.all([api.datasets(filters.cityId ? Number(filters.cityId) : undefined), api.coverage(filters.cityId ? Number(filters.cityId) : undefined), api.quality(), api.analytics('air_quality', params), api.analytics('road_safety', params)])
      .then(([datasets, coverage, quality, air, safety]) => {
        if (active) setData({ datasets: datasets.data, datasetTotal: datasets.meta.total, coverage: coverage.data, coverageCapped: coverage.meta.count >= coverage.meta.limit, quality: quality.data,
          airCount: air.data.reduce((total, row) => total + row.observation_count, 0),
          safetyCount: safety.data.reduce((total, row) => total + row.observation_count, 0),
          airCapped: air.meta.warnings.some((warning) => warning.includes('capped at 1000')), safetyCapped: safety.meta.warnings.some((warning) => warning.includes('capped at 1000')) })
      }).catch((reason: Error) => { if (active) setError(reason.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [filters.cityId, filters.startDate, filters.endDate])

  return <div className="space-y-6">
    <section className="relative overflow-hidden rounded-2xl bg-[#102a43] px-6 py-7 text-white sm:px-8 sm:py-9"><div className="absolute -right-8 -top-20 h-72 w-72 rounded-full border border-white/10" /><div className="absolute -right-1 top-0 h-52 w-52 rounded-full border border-white/10" /><div className="relative max-w-3xl"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-200">Urban conditions · evidence-led</p><h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Understand the city through its data.</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-blue-100/80">Explore verified urban datasets with source attribution, geographic coverage, and clear reporting periods. Availability varies by city and domain.</p><p className="mt-4 text-xs text-blue-200">Current view: <span className="font-semibold text-white">{selectedCity ? `${selectedCity.name}, ${selectedCity.state}` : 'All available cities'}</span></p></div></section>
    {loading ? <LoadingPanel label="Loading dashboard records" /> : error ? <ErrorPanel message={error} /> : !data ? <EmptyPanel /> : <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Registered datasets" value={data.datasetTotal} detail="Dataset records in the current city scope" icon={Database} /><MetricCard label="Coverage entries" value={`${data.coverageCapped ? '≥ ' : ''}${data.coverage.length}`} detail="Declared dataset and geography coverage records" icon={Layers3} /><MetricCard label="Air quality observations" value={`${data.airCapped ? '≥ ' : ''}${data.airCount.toLocaleString('en-IN')}`} detail={`${data.airCapped ? 'Returned groups are capped; lower bound ' : ''}normalized records matching filters`} icon={Activity} /><MetricCard label="Road safety observations" value={`${data.safetyCapped ? '≥ ' : ''}${data.safetyCount.toLocaleString('en-IN')}`} detail={`${data.safetyCapped ? 'Returned groups are capped; lower bound ' : ''}normalized records matching filters`} icon={ShieldCheck} /></section>
      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]"><div className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex items-start justify-between gap-4"><div><h3 className="text-base font-semibold text-slate-900">Data availability</h3><p className="mt-1 text-sm text-slate-500">Availability is based on declared dataset coverage for this selection.</p></div><Layers3 className="h-5 w-5 text-blue-800" /></div>{data.coverage.length ? <div className="mt-4 divide-y divide-slate-100">{data.coverage.slice(0, 8).map((entry, index) => { const dataset = data.datasets.find((item) => item.id === entry.dataset_id); return <div key={`${entry.dataset_id}-${entry.city_id}-${index}`} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="text-sm font-medium text-slate-800">{dataset?.name ?? `Dataset ${entry.dataset_id}`}</p><p className="mt-0.5 text-xs text-slate-500">{entry.geographic_level}{entry.period_start || entry.period_end ? ` · ${entry.period_start ?? 'Period start not reported'} to ${entry.period_end ?? 'Period end not reported'}` : ''}</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium capitalize text-slate-600">{entry.status.replaceAll('_', ' ')}</span></div>})}</div> : <div className="mt-4"><EmptyPanel title="Coverage not declared" >No dataset coverage entries match these filters. This does not mean measurements are zero.</EmptyPanel></div>}</div>
        <div className="space-y-5"><div className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-blue-800" /><h3 className="text-base font-semibold text-slate-900">Analytical modules</h3></div><div className="mt-3 divide-y divide-slate-100">{[{ name: 'Air quality', path: '/air-quality', count: data.airCount }, { name: 'Road safety', path: '/road-safety', count: data.safetyCount }, { name: 'Traffic & mobility', path: '/mobility' }, { name: 'Water & resources', path: '/water' }, { name: 'Urban development', path: '/urban-development' }].map((item) => <Link key={item.path} to={item.path} className="flex items-center justify-between py-3 text-sm hover:text-blue-800"><span className="font-medium">{item.name}</span><span className="text-xs text-slate-500">{item.count === undefined ? 'Open module' : `${item.count.toLocaleString('en-IN')} observations`}</span></Link>)}</div></div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5"><h3 className="text-sm font-semibold text-amber-950">Data freshness</h3><p className="mt-1.5 text-sm leading-6 text-amber-900">Refresh timestamps are not yet exposed through the API. Check each dataset’s reported period and source before treating records as current.</p></div>
          <div className="rounded-xl border border-slate-200 bg-white p-5"><h3 className="text-sm font-semibold text-slate-900">Recent quality reports</h3>{data.quality.length ? <ul className="mt-3 space-y-2">{data.quality.slice(0, 3).map((item) => <li key={item.id} className="flex justify-between gap-3 text-xs"><span className="text-slate-600">Dataset {item.dataset_id} · {item.rows_checked.toLocaleString('en-IN')} rows checked</span><span className="shrink-0 text-slate-500">{new Date(item.generated_at).toLocaleDateString('en-IN')}</span></li>)}</ul> : <p className="mt-2 text-sm text-slate-500">No quality reports are available yet.</p>}</div></div></section>
    </>}
  </div>
}
