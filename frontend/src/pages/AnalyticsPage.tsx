import { lazy, Suspense, useEffect, useState } from 'react'
import { Activity, Database, Info } from 'lucide-react'
import { useFilters } from '../app/FilterContext'
import { AnalyticsTable } from '../components/DataTable'
import { EmptyPanel, ErrorPanel, LoadingPanel } from '../components/StatePanel'
import { api } from '../services/api'
import type { AnalyticsResponse, Dataset, GeographicAreaOption } from '../types/api'

const AnalyticsChart = lazy(() => import('../components/AnalyticsChart').then((module) => ({ default: module.AnalyticsChart })))
const StationsMap = lazy(() => import('../components/StationsMap').then((module) => ({ default: module.StationsMap })))

const pageCopy: Record<string, { title: string; description: string; sourceNote: string }> = {
  air_quality: { title: 'Air quality analytics', description: 'Explore available pollutant observations by location and reporting period.', sourceNote: 'Pollutant values remain separated by dataset and unit.' },
  traffic: { title: 'Traffic & mobility analytics', description: 'Review traffic measures reported by available city and area datasets.', sourceNote: 'Measures are summarized as mean, minimum, and maximum; no totals are inferred.' },
  road_safety: { title: 'Road safety analytics', description: 'Explore reported road safety observations with their original geography and period.', sourceNote: 'Reported counts are not combined across categories or periods.' },
  water: { title: 'Water & resources analytics', description: 'Review water and resource indicators published for the selected geography.', sourceNote: 'Measurements are grouped by their normalized unit and source dataset.' },
  population: { title: 'Population indicators', description: 'Compare available demographic indicators by reference year and geographic coverage.', sourceNote: 'Population records retain their stated reference year; historical census values are not presented as current.' },
  infrastructure: { title: 'Infrastructure inventory', description: 'Review infrastructure records available through imported or connected datasets.', sourceNote: 'Asset coverage reflects the source dataset and its reported geographic level.' },
}

export function AnalyticsPage({ domain }: { domain: keyof typeof pageCopy }) {
  const filters = useFilters()
  const [result, setResult] = useState<AnalyticsResponse | null>(null)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [areas, setAreas] = useState<GeographicAreaOption[]>([])
  const [datasetId, setDatasetId] = useState('')
  const [areaId, setAreaId] = useState('')
  const [category, setCategory] = useState('')
  const [unit, setUnit] = useState('')
  const [geographicLevel, setGeographicLevel] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const copy = pageCopy[domain]
  const categoryLabel = domain === 'air_quality' ? 'Pollutant' : domain === 'population' ? 'Indicator' : domain === 'infrastructure' ? 'Asset type' : 'Measure'

  useEffect(() => {
    let active = true
    setDatasets([])
    setDatasetId('')
    api.datasets(filters.cityId ? Number(filters.cityId) : undefined).then(({ data }) => {
      const aliases: Record<string, string[]> = { road_safety: ['road_safety', 'road_accidents'], traffic: ['traffic', 'traffic_statistics'], water: ['water', 'water_statistics'], population: ['population', 'population_statistics'], air_quality: ['air_quality'], infrastructure: ['infrastructure'] }
      if (active) setDatasets(data.filter((dataset) => (aliases[domain] ?? [domain]).includes(dataset.domain.toLowerCase().replaceAll(' ', '_'))))
    }).catch((reason: Error) => { if (active) setError(reason.message) })
    return () => { active = false }
  }, [domain, filters.cityId])

  useEffect(() => {
    let active = true
    setAreaId('')
    api.areas(filters.cityId ? Number(filters.cityId) : undefined).then(({ data }) => {
      if (active) setAreas(data)
    }).catch(() => { if (active) setAreas([]) })
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
    api.analytics(domain, params).then((response) => {
      if (active) setResult(response)
    }).catch((reason: Error) => {
      if (active) setError(reason.message)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [domain, datasetId, areaId, category, unit, geographicLevel, filters.cityId, filters.startDate, filters.endDate])

  const comparableSeries = Boolean(datasetId && category && unit && geographicLevel && result?.data.length && !result.meta.warnings.some((warning) => warning.includes('capped at 1000')))

  return <div className="space-y-5">
    <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-800">Domain analysis</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{copy.title}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{copy.description}</p></div><div className="inline-flex items-center gap-2 self-start rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 md:self-auto"><Activity className="h-4 w-4 text-blue-700" />Filter-aware data view</div></section>
    <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 xl:grid-cols-5"><label className="text-xs font-semibold text-slate-600">Dataset<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All matching datasets</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select></label><label className="text-xs font-semibold text-slate-600">Area<select value={areaId} onChange={(event) => setAreaId(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All areas</option>{areas.map((area) => <option key={area.id} value={area.id}>{area.name} · {area.area_type}{area.city ? ` · ${area.city}` : ''}</option>)}</select></label><label className="text-xs font-semibold text-slate-600">{categoryLabel}<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Optional exact value" className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-blue-600" /></label><label className="text-xs font-semibold text-slate-600">Normalized unit<input value={unit} onChange={(event) => setUnit(event.target.value)} placeholder="Optional exact unit" className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-blue-600" /></label><label className="text-xs font-semibold text-slate-600">Geographic level<select value={geographicLevel} onChange={(event) => setGeographicLevel(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All reported levels</option>{['city', 'ward', 'station', 'district', 'state', 'other'].map((value) => <option key={value} value={value}>{value}</option>)}</select></label></section>
    <div className="flex flex-col gap-3 rounded-xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm text-blue-950 sm:flex-row sm:items-start"><Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" /><p>{copy.sourceNote} Each result includes observation count, reporting period, geographic coverage, and source attribution.</p></div>
    {loading ? <LoadingPanel label="Loading verified records" /> : error ? <ErrorPanel message={error} /> : !result?.data.length ? <EmptyPanel><span>{result?.meta.message ?? 'No normalized observations are available for the selected city and period.'} Imported files remain unavailable to analytics until they are processed.</span></EmptyPanel> : <>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><p className="inline-flex items-center gap-1.5"><Database className="h-3.5 w-3.5" />{result.meta.group_count.toLocaleString('en-IN')} grouped result{result.meta.group_count === 1 ? '' : 's'}</p><p>{result.calculation}</p></div>
      {result.insights.map((insight) => <section key={insight.name} className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">Highest recorded value · selected comparable series</p><p className="mt-1 text-sm text-emerald-950">{insight.method}</p><div className="mt-3 flex flex-wrap gap-3">{insight.winners.map((winner, index) => <div key={`${String(winner.city_id)}-${index}`} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm"><span className="font-semibold">{String(winner.city)}</span><span className="mx-2 text-emerald-600">{String(winner.maximum_recorded)} {String(winner.unit)}</span><span className="text-xs text-slate-500">{String(winner.observation_count)} observations</span></div>)}</div></section>)}
      {result.meta.warnings.map((warning) => <p key={warning} className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{warning}</p>)}
      {comparableSeries ? <Suspense fallback={<LoadingPanel label="Loading chart" />}><AnalyticsChart rows={result.data} title="Mean value by reported location" unit={unit} /></Suspense> : <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-3 text-xs leading-5 text-slate-500">Choose one dataset, category, unit, and geographic level to chart a comparable series. The table below keeps all available groups separate.</div>}
      <AnalyticsTable rows={result.data} />
    </>}
    {domain === 'air_quality' && <Suspense fallback={<LoadingPanel label="Loading station map" />}><StationsMap cityId={filters.cityId ? Number(filters.cityId) : undefined} datasetId={datasetId ? Number(datasetId) : undefined} areaId={areaId ? Number(areaId) : undefined} /></Suspense>}
  </div>
}
