export type BillingType = 'billable' | 'non-billable'
export type Priority = 'high' | 'medium' | 'low'
export type TaskStatus = 'created' | 'failed' | 'warning'

// Sentinel value: when Claude cannot determine hours, it returns exactly 1.0.
// The backend always returns estimated_hours as a number (never null).
export const HOURS_SENTINEL = 1.0

export interface Task {
  row_id: string
  task_name: string
  description: string
  assignee_name: string | null
  estimated_hours: number
  billing_type: BillingType
  sprint_milestone: string | null
  priority: Priority | null
  dependencies: string[]
  start_date: string | null  // YYYY-MM-DD
  end_date: string | null    // YYYY-MM-DD
  _hours_defaulted?: boolean  // true when AI returned sentinel 1.0 — amber highlight in UI
}

export interface ZohoProject { id: string; name: string }
export interface ZohoMember { id: string; name: string }
export interface ZohoMilestone { id: string; name: string }

export interface ExtractRequest {
  sow_text: string
  team_members: string[]
}

export interface PushRequest {
  project_id: string
  tasks: Task[]
}

export interface PushTaskResult {
  row_id: string
  task_name: string
  status: TaskStatus
  zoho_task_id: string | null
  warnings: string[]
  error: string | null
}

export interface PushResponse {
  results: PushTaskResult[]
}
