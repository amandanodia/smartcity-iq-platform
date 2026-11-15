import { useEffect, useMemo, useState } from 'react'
import { CircleAlert, MapPin } from 'lucide-react'
import { divIcon } from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../services/api'
import type { MonitoringStation } from '../types/api'
import { EmptyPanel, ErrorPanel, LoadingPanel } from './StatePanel'

const markerIcon = divIcon({ className: 'station-pin', html: '<span></span>', iconSize: [18, 18], iconAnchor: [9, 9] })

function FitStations({ stations }: { stations: MonitoringStation[] }) {
  const map = useMap()
  useEffect(() => {
    if (stations.length === 1) {
      map.setView([stations[0].latitude, stations[0].longitude], 11)
    } else if (stations.length > 1) {
      map.fitBounds(stations.map((station) => [station.latitude, station.longitude] as [number, number]), { padding: [28, 28], maxZoom: 11 })
    }
  }, [map, stations])
  return null
}

export function StationsMap({ cityId, datasetId, areaId }: { cityId?: number; datasetId?: number; areaId?: number }) {
  const [stations, setStations] = useState<MonitoringStation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [capped, setCapped] = useState(false)
  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    api.stations(cityId, datasetId, areaId).then((response) => {
      if (active) { setStations(response.data); setCapped(response.meta.capped) }
    }).catch((reason: Error) => { if (active) setError(reason.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [cityId, datasetId, areaId])

  const center = useMemo<[number, number]>(() => stations.length ? [stations[0].latitude, stations[0].longitude] : [0, 0], [stations])

  return <section className="space-y-3"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-800">Geographic coverage</p><h3 className="mt-1 text-lg font-semibold text-slate-900">Monitoring station locations</h3><p className="mt-1 text-sm text-slate-500">Only coordinates stored with registered station records are plotted. Map pins are not pollutant readings.</p></div><div className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600"><MapPin className="h-3.5 w-3.5 text-blue-800" />{stations.length.toLocaleString('en-IN')} mapped station{stations.length === 1 ? '' : 's'}{capped ? ' · capped at 500' : ''}</div></div>
    {loading ? <LoadingPanel label="Loading station coordinates" /> : error ? <ErrorPanel message={error} /> : !stations.length ? <EmptyPanel title="No mapped stations available">No registered monitoring stations with valid coordinates match these filters. A map is unavailable until source-verified coordinates are imported.</EmptyPanel> : <><div className="overflow-hidden rounded-xl border border-slate-200 bg-white"><MapContainer center={center} zoom={5} scrollWheelZoom={false} className="h-[420px] w-full"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url={import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'} /><FitStations stations={stations} />{stations.map((station) => <Marker key={station.id} position={[station.latitude, station.longitude]} icon={markerIcon}><Popup><div className="min-w-44"><p className="font-semibold">{station.name}</p><p className="mt-1 text-xs text-slate-600">{station.city ? `${station.city}${station.state ? `, ${station.state}` : ''}` : 'City not reported'}</p><p className="mt-1 text-xs text-slate-600">{station.dataset} · {station.record_class.replaceAll('_', ' ')}</p><p className="mt-1 text-[11px] text-slate-500">{station.latitude.toFixed(5)}, {station.longitude.toFixed(5)}</p><a href={station.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs font-medium text-blue-800">Open source</a></div></Popup></Marker>)}</MapContainer></div>{capped && <p className="flex gap-2 text-xs text-amber-800"><CircleAlert className="h-4 w-4 shrink-0" />The map is limited to 500 station records. Narrow by city or dataset to inspect coverage.</p>}<p className="text-[11px] leading-5 text-slate-500">Basemap tiles © OpenStreetMap contributors. Tile service availability is best effort. Station coordinates and source links come from registered dataset records.</p></>}
  </section>
}
