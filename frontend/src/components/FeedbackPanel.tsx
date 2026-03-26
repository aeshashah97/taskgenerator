import type { PushTaskResult } from '../types/task'

interface Props {
  results: PushTaskResult[]
}

const BORDER_CLASS: Record<string, string> = {
  created: 'border-l-4 border-green-500',
  warning: 'border-l-4 border-amber-500',
  failed:  'border-l-4 border-red-500',
}

const PILL_CLASS: Record<string, string> = {
  created: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  failed:  'bg-red-100 text-red-800',
}

const PILL_LABEL: Record<string, string> = {
  created: 'Created',
  warning: 'Warnings',
  failed:  'Failed',
}

export function FeedbackPanel({ results }: Props) {
  if (results.length === 0) return null

  const counts = results.reduce(
    (acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }),
    {} as Record<string, number>
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 flex-wrap">
        {(['created', 'warning', 'failed'] as const).map((status) =>
          counts[status] ? (
            <span key={status} className={`text-sm font-semibold px-3 py-1 rounded-full ${PILL_CLASS[status]}`}>
              {counts[status]} {PILL_LABEL[status]}
            </span>
          ) : null
        )}
      </div>
      <div className="flex flex-col gap-2">
        {results.map((result) => (
          <div key={result.row_id}
            className={`flex flex-col gap-1 p-3 rounded-lg bg-white shadow-sm ${BORDER_CLASS[result.status] ?? 'border-l-4 border-slate-300'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${PILL_CLASS[result.status]}`}>
                {result.status}
              </span>
              <span className="text-sm font-medium text-slate-800">{result.task_name}</span>
              {result.zoho_task_id && (
                <span className="text-xs text-slate-400 ml-auto">#{result.zoho_task_id}</span>
              )}
            </div>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-xs text-amber-700 ml-1">⚠ {w}</p>
            ))}
            {result.error && (
              <p className="text-xs text-red-600 ml-1">✕ {result.error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
