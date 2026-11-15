import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../services/api'
import type { City } from '../types/api'

interface Filters {
  cities: City[]
  cityId: string
  startDate: string
  endDate: string
  citiesLoading: boolean
  citiesError: string | null
  setCityId: (value: string) => void
  setStartDate: (value: string) => void
  setEndDate: (value: string) => void
  analyticsParams: (domain?: string) => Record<string, string | number | undefined>
}

const FilterContext = createContext<Filters | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [cities, setCities] = useState<City[]>([])
  const [cityId, setCityId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [citiesLoading, setCitiesLoading] = useState(true)
  const [citiesError, setCitiesError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api.cities().then(({ data }) => {
      if (active) setCities(data)
    }).catch((error: Error) => {
      if (active) setCitiesError(error.message)
    }).finally(() => {
      if (active) setCitiesLoading(false)
    })
    return () => { active = false }
  }, [])

  const value = useMemo<Filters>(() => ({
    cities, cityId, startDate, endDate, citiesLoading, citiesError,
    setCityId, setStartDate, setEndDate,
    analyticsParams: (domain?: string) => {
      const params: Record<string, string | number | undefined> = {
        city_id: cityId ? Number(cityId) : undefined,
        timezone: 'Asia/Kolkata',
      }
      if (domain === 'population') {
        params.year_from = startDate ? Number(startDate.slice(0, 4)) : undefined
        params.year_to = endDate ? Number(endDate.slice(0, 4)) : undefined
      } else {
        params.start_date = startDate || undefined
        params.end_date = endDate || undefined
      }
      return params
    },
  }), [cities, cityId, startDate, endDate, citiesLoading, citiesError])

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useFilters() {
  const value = useContext(FilterContext)
  if (!value) throw new Error('useFilters must be used inside FilterProvider')
  return value
}
