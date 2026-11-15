import type { ApiErrorBody, AnalyticsResponse, City, Coverage, DataSource, Dataset, GeographicAreaOption, MonitoringStation, QualityReport } from '../types/api'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}/api${path}`, window.location.origin)
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value))
  })
  let response: Response
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError('The API could not be reached. Check that the backend is running.', 0)
  }
  const body = await response.json().catch(() => ({})) as ApiErrorBody
  if (!response.ok) {
    throw new ApiError(body.error?.message ?? `Request failed (${response.status}).`, response.status, body.error?.code)
  }
  return body as T
}

export const api = {
  health: () => get<{ status: string; database: string }>('/health'),
  cities: () => get<{ data: City[] }>('/cities'),
  datasets: (cityId?: number) => get<{ data: Dataset[]; meta: { total: number } }>('/datasets', { city_id: cityId, per_page: 100 }),
  coverage: (cityId?: number) => get<{ data: Coverage[]; meta: { count: number; limit: number } }>('/datasets/coverage', { city_id: cityId }),
  analytics: (domain: string, params: Record<string, string | number | undefined>) =>
    get<AnalyticsResponse>(`/analytics/${domain}`, params),
  comparison: (domain: string, params: Record<string, string | number | undefined>) =>
    get<AnalyticsResponse>('/analytics/city-comparison', { ...params, domain }),
  dataSources: () => get<{ data: DataSource[] }>('/data-sources'),
  stations: (cityId?: number, datasetId?: number, areaId?: number) => get<{ data: MonitoringStation[]; meta: { count: number; limit: number; capped: boolean; message: string | null } }>('/monitoring-stations', { city_id: cityId, dataset_id: datasetId, area_id: areaId }),
  areas: (cityId?: number, areaType?: string) => get<{ data: GeographicAreaOption[]; meta: { count: number; limit: number; capped: boolean } }>('/geographic-areas', { city_id: cityId, area_type: areaType }),
  quality: () => get<{ data: QualityReport[]; meta: { total: number; pages: number } }>('/data-quality', { per_page: 100 }),
}
