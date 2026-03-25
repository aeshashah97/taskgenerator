import type { Task } from '../types/task'

export interface ValidationError {
  row_id: string
  fields: string[]
}

export function validateTasksForPush(tasks: Task[]): ValidationError[] {
  return tasks.flatMap((task) => {
    const fields: string[] = []
    if (!task.task_name.trim()) fields.push('task_name')
    if (!task.description.trim()) fields.push('description')
    if (task.assignee_names.length === 0) fields.push('assignee_names')
    const hours = task.estimated_hours
    if (hours !== null && hours !== undefined && (isNaN(hours) || hours < 0.5 || hours > 999)) fields.push('estimated_hours')
    if (!task.billing_type) fields.push('billing_type')
    if (task.start_date && task.end_date && task.end_date < task.start_date) {
      fields.push('end_date')
    }
    return fields.length > 0 ? [{ row_id: task.row_id, fields }] : []
  })
}

export function isPushReady(tasks: Task[]): boolean {
  if (tasks.length === 0) return false  // check length first: no tasks → not ready
  return validateTasksForPush(tasks).length === 0
}
