import type { ReactNode } from 'react'
import { AlertCircle, Database, LoaderCircle } from 'lucide-react'

export function LoadingPanel({ label = 'Loading data' }: { label?: string }) {
  return <div className="flex min-h-40 items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin text-blue-700" />{label}</div>
}

export function ErrorPanel({ message }: { message: string }) {
  return <div role="alert" className="flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="font-semibold">Data request failed</p><p className="mt-1">{message}</p></div></div>
}

export function EmptyPanel({ title = 'No records available', children }: { title?: string; children?: ReactNode }) {
  return <div className="flex min-h-52 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 text-center"><span className="grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-500"><Database className="h-5 w-5" /></span><h3 className="mt-3 text-sm font-semibold text-slate-800">{title}</h3><div className="mt-1 max-w-md text-sm leading-6 text-slate-500">{children ?? 'The selected filters do not have published measurements in the connected datasets.'}</div></div>
}
