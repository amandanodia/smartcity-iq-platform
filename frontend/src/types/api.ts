export interface City {
  id: number
  name: string
  state: string
  slug: string
}

export interface Dataset {
  id: number
  name: string
  domain: string
  source_id: number
  source_url: string
  record_class: 'live' | 'historical' | 'manually_imported' | 'sample' | string
}

export interface Coverage {
  dataset_id: number
  city_id: number | null
  area_id: number | null
  geographic_level: string
  period_start: string | null
  period_end: string | null
  status: string
  notes: string | null
}

export interface AnalyticsRow {
  city_id: number | null
  city: string | null
  category: string | null
  category_type: string
  unit: string | null
  observation_count: number
  mean: number | null
  maximum_recorded: number | null
  minimum_recorded: number | null
  reporting_period: { start: string | null; end: string | null }
  coverage: { city: string | null; state: string | null; geographic_level: string; area: string | null }
  dataset: { id: number; name: string; record_class: string; source: string; source_url: string; attribution?: string | null; license?: string | null }
}

export interface AnalyticsResponse {
  domain: string
  calculation: string
  filters: Record<string, string | number | null>
  data: AnalyticsRow[]
  insights: Array<{ name: string; method: string; winners: Array<Record<string, unknown>> }>
  meta: { group_count: number; warnings: string[]; message: string | null; insight_note?: string | null }
}

export interface DataSource {
  id: number
  name: string
  base_url: string | null
  access_method: string
  license: string | null
  license_url: string | null
  attribution: string | null
}

export interface QualityReport {
  id: number
  dataset_id: number
  import_batch_id: number | null
  generated_at: string
  rows_checked: number
  duplicate_rows: number
  missing_value_counts: Record<string, number>
  warnings: string[]
}

export interface MonitoringStation {
  id: number
  name: string
  latitude: number
  longitude: number
  active: boolean | null
  city_id: number | null
  city: string | null
  state: string | null
  dataset_id: number
  dataset: string
  record_class: string
  source_url: string
}

export interface GeographicAreaOption {
  id: number
  city_id: number | null
  city: string | null
  state: string | null
  name: string
  area_type: string
  parent_id: number | null
}

export interface ApiErrorBody {
  error?: { code?: string; message?: string }
}
