import { useState, useEffect } from 'react'
import type { ZohoMember } from '../types/task'
import { fetchMembers } from '../api/client'

export function useProjectMembers(projectId: string | null) {
  const [members, setMembers] = useState<ZohoMember[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) { setMembers([]); return }
    let cancelled = false
    setLoading(true)
    fetchMembers(projectId)
      .then((data) => { if (!cancelled) setMembers(data) })
      .catch(() => { if (!cancelled) setMembers([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId])

  return { members, loading }
}
