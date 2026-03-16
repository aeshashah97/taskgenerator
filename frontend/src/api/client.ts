import type {
  ZohoProject, ZohoMember, ZohoMilestone,
  ExtractRequest, Task, PushRequest, PushResponse,
} from '../types/task'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const err = new Error(body.detail ?? `HTTP ${response.status}`) as Error & {
      status: number
      body: unknown
    }
    err.status = response.status
    err.body = body
    throw err
  }
  return response.json() as Promise<T>
}

export async function fetchProjects(): Promise<ZohoProject[]> {
  const data = await apiFetch<{ projects: ZohoProject[] }>('/zoho/projects')
  return data.projects
}

export async function fetchMembers(projectId: string): Promise<ZohoMember[]> {
  const data = await apiFetch<{ members: ZohoMember[] }>(`/zoho/projects/${projectId}/members`)
  return data.members
}

export async function fetchMilestones(projectId: string): Promise<ZohoMilestone[]> {
  const data = await apiFetch<{ milestones: ZohoMilestone[] }>(`/zoho/projects/${projectId}/milestones`)
  return data.milestones
}

export async function fetchGoogleDoc(url: string): Promise<string> {
  const encoded = encodeURIComponent(url)
  const data = await apiFetch<{ text: string }>(`/google-doc?url=${encoded}`)
  return data.text
}

export async function extractTasks(request: ExtractRequest): Promise<Task[]> {
  const data = await apiFetch<{ tasks: Task[] }>('/extract', {
    method: 'POST',
    body: JSON.stringify(request),
  })
  return data.tasks
}

export async function pushTasks(request: PushRequest): Promise<PushResponse> {
  return apiFetch<PushResponse>('/push', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
