import { lazy, Suspense, useEffect, useState } from 'react'
import { ArrowLeftRight, Info } from 'lucide-react'
import { useFilters } from '../app/FilterContext'
import { AnalyticsTable } from '../components/DataTable'
import { EmptyPanel, ErrorPanel, LoadingPanel } from '../components/StatePanel'
import { api } from '../services/api'
import type { AnalyticsResponse, Dataset, GeographicAreaOption } from '../types/api'

const AnalyticsChart = lazy(() => import('../components/AnalyticsChart').then((module) => ({ default: module.AnalyticsChart })))

const domains = [
  ['air_quality', 'Air quality'], ['traffic', 'Traffic & mobility'], ['road_safety', 'Road safety'],
  ['water', 'Water & resources'], ['population', 'Population'], ['infrastructure', 'Infrastructure'],
]

export function ComparisonPage() {
  const filters = useFilters()
  const [domain, setDomain] = useState('air_quality')
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [areas, setAreas] = useState<GeographicAreaOption[]>([])
  const [datasetId, setDatasetId] = useState('')
  const [areaId, setAreaId] = useState('')
  const [category, setCategory] = useState('')
  const [unit, setUnit] = useState('')
  const [geographicLevel, setGeographicLevel] = useState('')
  const [result, setResult] = useState<AnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setDatasets([])
    setDatasetId('')
    api.datasets(filters.cityId ? Number(filters.cityId) : undefined).then(({ data }) => {
      const aliases: Record<string, string[]> = { road_safety: ['road_safety', 'road_accidents'], traffic: ['traffic', 'traffic_statistics'], water: ['water', 'water_statistics'], population: ['population', 'population_statistics'], air_quality: ['air_quality'] }
      if (active) setDatasets(data.filter((dataset) => (aliases[domain] ?? [domain]).includes(dataset.domain.toLowerCase().replaceAll(' ', '_'))))
    }).catch((reason: Error) => { if (active) setError(reason.message) })
    return () => { active = false }
  }, [domain, filters.cityId])

  useEffect(() => {
    let active = true
    setAreaId('')
    api.areas(filters.cityId ? Number(filters.cityId) : undefined).then(({ data }) => { if (active) setAreas(data) }).catch(() => { if (active) setAreas([]) })
    return () => { active = false }
  }, [filters.cityId])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    const params = { ...filters.analyticsParams(domain), dataset_id: datasetId ? Number(datasetId) : undefined,
      area_id: areaId ? Number(areaId) : undefined,
      pollutant: domain === 'air_quality' ? category || undefined : undefined,
      measure: domain !== 'air_quality' && !['population', 'infrastructure'].includes(domain) ? category || undefined : undefined,
      indicator: domain === 'population' ? category || undefined : undefined,
      asset_type: domain === 'infrastructure' ? category || undefined : undefined,
      unit: unit || undefined, geographic_level: geographicLevel || undefined }
    api.comparison(domain, params).then((response) => { if (active) setResult(response) })
      .catch((reason: Error) => { if (active) setError(reason.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [domain, datasetId, areaId, category, unit, geographicLevel, filters.cityId, filters.startDate, filters.endDate])

  const categoryLabel = domain === 'air_quality' ? 'Pollutant' : domain === 'population' ? 'Indicator' : domain === 'infrastructure' ? 'Asset type' : 'Measure'
  const comparableSeries = Boolean(datasetId && category && unit && geographicLevel && result?.data.length && !result.meta.warnings.some((warning) => warning.includes('capped at 1000')))

  return <div className="space-y-5"><section><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-800">Cross-city analysis</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Compare reported urban indicators</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Results remain grouped by source dataset, geography, category, and unit. A highest-recorded comparison appears only when the selected series is comparable.</p></section>
    <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 xl:grid-cols-6"><label className="text-xs font-semibold text-slate-600">Domain<select value={domain} onChange={(event) => { setDomain(event.target.value); setCategory(''); setUnit(''); setGeographicLevel('') }} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800">{domains.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label className="text-xs font-semibold text-slate-600">Dataset<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All matching datasets</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select></label>
      <label className="text-xs font-semibold text-slate-600">Area<select value={areaId} onChange={(event) => setAreaId(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All areas</option>{areas.map((area) => <option key={area.id} value={area.id}>{area.name} · {area.area_type}{area.city ? ` · ${area.city}` : ''}</option>)}</select></label>
      <label className="text-xs font-semibold text-slate-600">{categoryLabel}<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Optional exact value" className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-blue-600" /></label>
      <label className="text-xs font-semibold text-slate-600">Normalized unit<input value={unit} onChange={(event) => setUnit(event.target.value)} placeholder="e.g. µg/m³" className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-blue-600" /></label>
      <label className="text-xs font-semibold text-slate-600">Geographic level<select value={geographicLevel} onChange={(event) => setGeographicLevel(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All reported levels</option>{['city', 'ward', 'station', 'district', 'state', 'other'].map((value) => <option key={value} value={value}>{value}</option>)}</select></label></section>
    <div className="flex gap-3 rounded-xl border border-blue-100 bg-blue-50/70 p-4 text-sm text-blue-950"><Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" /><p>For a direct highest-recorded comparison, choose one dataset, category, unit, and geographic level. Different sources or units are not silently combined.</p></div>
    {loading ? <LoadingPanel label="Comparing available records" /> : error ? <ErrorPanel message={error} /> : !result?.data.length ? <EmptyPanel title="No comparable records available">No normalized records match the chosen domain and filters. Imported data must be processed before it appears here.</EmptyPanel> : <><div className="flex items-center gap-2 text-xs text-slate-500"><ArrowLeftRight className="h-4 w-4" />{result.meta.group_count} source/geography groups</div>{result.insights.map((insight) => <div key={insight.name} className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">Highest recorded · comparable selected series</p><p className="mt-1 text-sm text-emerald-950">{insight.method}</p><div className="mt-3 flex flex-wrap gap-2">{insight.winners.map((winner, index) => <span key={index} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm"><strong>{String(winner.city)}</strong><span className="mx-2">{String(winner.maximum_recorded)} {String(winner.unit)}</span><span className="text-xs text-slate-500">n={String(winner.observation_count)}</span></span>)}</div></div>)}{result.meta.insight_note && <p className="text-xs text-slate-500">{result.meta.insight_note}</p>}{comparableSeries ? <Suspense fallback={<LoadingPanel label="Loading chart" />}><AnalyticsChart rows={result.data} title="City comparison · mean normalized value" unit={unit} /></Suspense> : <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-3 text-xs leading-5 text-slate-500">Select a single dataset, category, unit, and geographic level to chart a comparable series. No cross-source or cross-unit values are combined.</div>}<AnalyticsTable rows={result.data} /></>}
  </div>
}
