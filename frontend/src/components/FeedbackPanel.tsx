import type { PushTaskResult } from '../types/task'

interface Props {
  results: PushTaskResult[]
}

const STATUS_STYLES: Record<string, string> = {
  created: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  failed:  'bg-red-100 text-red-800',
}

export function FeedbackPanel({ results }: Props) {
  if (results.length === 0) return null

  const counts = results.reduce(
    (acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }),
    {} as Record<string, number>
  )

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3 text-sm font-medium">
        {counts.created ? <span className="text-green-700">{counts.created} created</span> : null}
        {counts.warning ? <span className="text-amber-700">{counts.warning} with warnings</span> : null}
        {counts.failed  ? <span className="text-red-700">{counts.failed} failed</span> : null}
      </div>
      <div className="flex flex-col gap-2">
        {results.map((result) => (
          <div key={result.row_id}
            className="flex flex-col gap-1 p-2 rounded border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLES[result.status]}`}>
                {result.status}
              </span>
              <span className="text-sm font-medium text-slate-800">{result.task_name}</span>
              {result.zoho_task_id && (
                <span className="text-xs text-slate-400">#{result.zoho_task_id}</span>
              )}
            </div>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-xs text-amber-700 ml-1" role="alert">Warning: {w}</p>
            ))}
            {result.error && (
              <p className="text-xs text-red-600 ml-1" role="alert">Error: {result.error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
