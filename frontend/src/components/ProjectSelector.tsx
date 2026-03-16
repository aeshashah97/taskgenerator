import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select'
import { useZohoProjects } from '../hooks/useZohoProjects'

interface Props {
  value: string | null
  onChange: (projectId: string) => void
}

export function ProjectSelector({ value, onChange }: Props) {
  const { projects, loading, error } = useZohoProjects()

  if (error) {
    return <p className="text-sm text-red-500">Failed to load Zoho projects: {error}</p>
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-slate-700">Zoho Project</label>
      <Select value={value ?? ''} onValueChange={onChange} disabled={loading}>
        <SelectTrigger className="w-64">
          <SelectValue placeholder={loading ? 'Loading projects…' : projects.length === 0 ? 'No projects found' : 'Select a project'} />
        </SelectTrigger>
        <SelectContent>
          {projects.map((p) => (
            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
