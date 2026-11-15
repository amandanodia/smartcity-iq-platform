import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity, BarChart3, ClipboardCheck, Droplets, Gauge, Globe2, LayoutDashboard, Menu, ShieldAlert,
  TrafficCone, Trees, X, type LucideIcon,
} from 'lucide-react'
import { api } from '../services/api'
import { GlobalFilters } from './GlobalFilters'

const navigation: Array<{ path: string; label: string; icon: LucideIcon }> = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/comparison', label: 'City comparison', icon: BarChart3 },
  { path: '/mobility', label: 'Traffic & mobility', icon: TrafficCone },
  { path: '/air-quality', label: 'Air quality', icon: Activity },
  { path: '/road-safety', label: 'Road safety', icon: ShieldAlert },
  { path: '/water', label: 'Water & resources', icon: Droplets },
  { path: '/urban-development', label: 'Urban development', icon: Trees },
  { path: '/data-sources', label: 'Data sources', icon: Globe2 },
  { path: '/data-quality', label: 'Data quality', icon: ClipboardCheck },
  { path: '/about', label: 'About project', icon: Gauge },
]

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [apiState, setApiState] = useState<'checking' | 'connected' | 'unavailable'>('checking')
  const location = useLocation()
  const pageTitle = navigation.find((item) => item.path === location.pathname)?.label ?? 'SmartCity IQ'

  useEffect(() => {
    let active = true
    api.health().then(() => { if (active) setApiState('connected') }).catch(() => { if (active) setApiState('unavailable') })
    return () => { active = false }
  }, [])

  const sideNav = <>
    <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-blue-500 text-white"><Activity className="h-5 w-5" /></div><div><p className="text-[15px] font-semibold tracking-wide text-white">SmartCity <span className="text-blue-300">IQ</span></p><p className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-slate-400">Urban intelligence</p></div></div>
    <div className="px-3 pt-5"><p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Workspace</p><nav className="space-y-1" aria-label="Main navigation">{navigation.map(({ path, label, icon: Icon }) => <NavLink key={path} to={path} end={path === '/'} onClick={() => setMobileOpen(false)} className={({ isActive }) => `group flex min-h-10 items-center gap-3 rounded-lg px-3 text-[13px] font-medium transition-colors ${isActive ? 'bg-blue-600 text-white shadow-sm shadow-blue-950/25' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}><Icon className="h-[17px] w-[17px] shrink-0" /><span>{label}</span></NavLink>)}</nav></div>
    <div className="mt-auto p-4"><div className="rounded-xl border border-white/10 bg-white/[0.04] p-3"><div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${apiState === 'connected' ? 'bg-emerald-400' : apiState === 'unavailable' ? 'bg-rose-400' : 'animate-pulse bg-amber-300'}`} /><p className="text-xs font-medium text-slate-200">{apiState === 'connected' ? 'API connected' : apiState === 'unavailable' ? 'API unavailable' : 'Checking API'}</p></div><p className="mt-1.5 text-[11px] leading-4 text-slate-400">{apiState === 'connected' ? 'Source-backed data services are responding.' : apiState === 'unavailable' ? 'Start the backend to load live application records.' : 'Checking service availability.'}</p></div><p className="mt-4 px-1 text-[10px] text-slate-500">SmartCity IQ · India urban data</p></div>
  </>

  return <div className="min-h-screen bg-slate-50 text-slate-900">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[252px] flex-col bg-[#10243a] lg:flex">{sideNav}</aside>
    {mobileOpen && <div className="fixed inset-0 z-40 lg:hidden"><button className="absolute inset-0 bg-slate-950/40" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /><aside className="absolute inset-y-0 left-0 flex w-[285px] flex-col bg-[#10243a] shadow-xl">{sideNav}</aside></div>}
    <div className="lg:pl-[252px]">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur"><div className="flex h-[68px] items-center justify-between px-4 sm:px-6 xl:px-8"><div className="flex items-center gap-3"><button className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-700 lg:hidden" aria-label={mobileOpen ? 'Close menu' : 'Open menu'} onClick={() => setMobileOpen((value) => !value)}>{mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}</button><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-800">Indian urban intelligence platform</p><h1 className="mt-0.5 text-[17px] font-semibold tracking-tight text-slate-900">{pageTitle}</h1></div></div><div className="hidden items-center gap-2 text-xs text-slate-500 sm:flex"><span className={`h-2 w-2 rounded-full ${apiState === 'connected' ? 'bg-emerald-500' : apiState === 'unavailable' ? 'bg-rose-500' : 'bg-amber-400'}`} />{apiState === 'connected' ? 'Connected to API' : apiState === 'unavailable' ? 'Backend not connected' : 'Connecting'}</div></div></header>
      <main className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6 sm:py-7 xl:px-8"><div className="mb-5"><GlobalFilters /></div><Outlet /></main>
    </div>
  </div>
}
