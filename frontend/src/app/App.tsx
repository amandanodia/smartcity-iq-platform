import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { AboutPage } from '../pages/AboutPage'
import { ComparisonPage } from '../pages/ComparisonPage'
import { DashboardPage } from '../pages/DashboardPage'
import { DataSourcesPage } from '../pages/DataSourcesPage'
import { QualityPage } from '../pages/QualityPage'
import { FilterProvider } from './FilterContext'

export default function App() {
  return <FilterProvider><Routes><Route element={<AppLayout />}><Route index element={<DashboardPage />} /><Route path="comparison" element={<ComparisonPage />} /><Route path="mobility" element={<AnalyticsPage domain="traffic" />} /><Route path="air-quality" element={<AnalyticsPage domain="air_quality" />} /><Route path="road-safety" element={<AnalyticsPage domain="road_safety" />} /><Route path="water" element={<AnalyticsPage domain="water" />} /><Route path="urban-development" element={<div className="space-y-10"><AnalyticsPage domain="population" /><div className="border-t border-slate-200 pt-8"><AnalyticsPage domain="infrastructure" /></div></div>} /><Route path="data-sources" element={<DataSourcesPage />} /><Route path="data-quality" element={<QualityPage />} /><Route path="about" element={<AboutPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes></FilterProvider>
}
