import { useZohoProjects } from '../hooks/useZohoProjects'

interface Props {
  value: string | null
  onChange: (projectId: string, projectName: string) => void
}

export function ProjectSelector({ value, onChange }: Props) {
  const { projects, loading, error } = useZohoProjects()

  if (error) {
    return <p className="text-sm text-red-500">Failed to load Zoho projects: {error}</p>
  }

  return (
    <div className="flex flex-col gap-1 w-full">
      <label className="text-sm font-semibold text-slate-700">Zoho Project</label>
      <select
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        value={value ?? ''}
        onChange={(e) => {
          if (e.target.value) {
            const name = projects.find(p => p.id === e.target.value)?.name ?? ''
            onChange(e.target.value, name)
          }
        }}
        disabled={loading}
      >
        <option value="">
          {loading ? 'Loading projects…' : projects.length === 0 ? 'No projects found' : 'Select a project'}
        </option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
    </div>
  )
}
