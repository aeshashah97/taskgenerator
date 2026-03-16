import { useState, useEffect } from 'react'
import type { ZohoMilestone } from '../types/task'
import { fetchMilestones } from '../api/client'

export function useProjectMilestones(projectId: string | null) {
  const [milestones, setMilestones] = useState<ZohoMilestone[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) { setMilestones([]); return }
    let cancelled = false
    setLoading(true)
    fetchMilestones(projectId)
      .then((data) => { if (!cancelled) setMilestones(data) })
      .catch(() => { if (!cancelled) setMilestones([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId])

  return { milestones, loading }
}
