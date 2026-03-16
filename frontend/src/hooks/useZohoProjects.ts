import { useState, useEffect } from 'react'
import type { ZohoProject } from '../types/task'
import { fetchProjects } from '../api/client'

export function useZohoProjects() {
  const [projects, setProjects] = useState<ZohoProject[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchProjects()
      .then((data) => { if (!cancelled) setProjects(data) })
      .catch((e) => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  return { projects, loading, error }
}
