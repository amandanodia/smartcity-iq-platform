import { CalendarDays, MapPin, RotateCcw } from 'lucide-react'
import { useFilters } from '../app/FilterContext'

export function GlobalFilters() {
  const filters = useFilters()
  const reset = () => { filters.setCityId(''); filters.setStartDate(''); filters.setEndDate('') }
  return <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.02] sm:grid-cols-2 xl:grid-cols-[minmax(190px,1fr)_minmax(150px,0.8fr)_minmax(150px,0.8fr)_auto] xl:items-end">
    <label className="block"><span className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-slate-600"><MapPin className="h-3.5 w-3.5" />City</span><select value={filters.cityId} onChange={(event) => filters.setCityId(event.target.value)} disabled={filters.citiesLoading} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"><option value="">All available cities</option>{filters.cities.map((city) => <option key={city.id} value={city.id}>{city.name}, {city.state}</option>)}</select></label>
    <label className="block"><span className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-slate-600"><CalendarDays className="h-3.5 w-3.5" />From date / year</span><input aria-label="Start date" type="date" value={filters.startDate} onChange={(event) => filters.setStartDate(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" /></label>
    <label className="block"><span className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-slate-600"><CalendarDays className="h-3.5 w-3.5" />To date / year</span><input aria-label="End date" type="date" value={filters.endDate} onChange={(event) => filters.setEndDate(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" /></label>
    <button type="button" onClick={reset} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"><RotateCcw className="h-3.5 w-3.5" />Reset</button>
    {filters.citiesError && <p className="sm:col-span-2 xl:col-span-4 text-xs text-amber-800">City list unavailable: {filters.citiesError}</p>}
    <p className="sm:col-span-2 xl:col-span-4 text-xs text-slate-500">Date filters use India Standard Time. Population data is filtered by calendar year.</p>
  </div>
}
