import type { ReactNode } from 'react'

interface Props {
  step: 1 | 2 | 3 | 4
  title: string
  activeStep: number
  summary?: string
  onEdit?: () => void
  children: ReactNode
}

export function StepCard({ step, title, activeStep, summary, onEdit, children }: Props) {
  const completed = step < activeStep
  const active = step === activeStep
  const upcoming = step > activeStep

  if (completed) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">✓</span>
          <span className="text-sm font-semibold text-slate-700">{title}</span>
          {summary && <span className="text-sm text-slate-400">— {summary}</span>}
        </div>
        {onEdit && (
          <button onClick={onEdit} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
            Edit
          </button>
        )}
      </div>
    )
  }

  if (upcoming) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-5 opacity-40 pointer-events-none">
        <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">{title}</h2>
      </div>
    )
  }

  // active
  return (
    <div className="bg-white rounded-lg border border-slate-200 border-l-4 border-l-indigo-600 p-5">
      <h2 className="text-base font-bold text-slate-800 mb-4">{title}</h2>
      {children}
    </div>
  )
}
