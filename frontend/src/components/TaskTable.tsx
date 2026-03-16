import { v4 as uuidv4 } from 'uuid'
import type { Task, BillingType, Priority, ZohoMember, ZohoMilestone } from '../types/task'
import { validateTasksForPush } from '../utils/validation'

interface Props {
  tasks: Task[]
  members: ZohoMember[]
  milestones: ZohoMilestone[]
  onChange: (tasks: Task[]) => void  // receives full updated task array
}

const BILLING_OPTIONS: BillingType[] = ['billable', 'non-billable']
const PRIORITY_OPTIONS: Priority[] = ['high', 'medium', 'low']

function emptyTask(): Task {
  return {
    row_id: uuidv4(),
    task_name: '',
    description: '',
    assignee_name: null,
    estimated_hours: 1.0,
    billing_type: 'billable',
    sprint_milestone: null,
    priority: null,
    dependencies: [],
    start_date: null,
    end_date: null,
  }
}

export function TaskTable({ tasks, members, milestones, onChange }: Props) {
  const errors = validateTasksForPush(tasks)
  const errorMap = Object.fromEntries(errors.map((e) => [e.row_id, new Set(e.fields)]))

  function update(row_id: string, patch: Partial<Task>) {
    onChange(tasks.map((t) => (t.row_id === row_id ? { ...t, ...patch } : t)))
  }

  function addRow() { onChange([...tasks, emptyTask()]) }
  function deleteRow(row_id: string) { onChange(tasks.filter((t) => t.row_id !== row_id)) }

  function cellClass(row_id: string, field: string, extra = '') {
    const hasError = errorMap[row_id]?.has(field)
    return `border rounded px-1 py-0.5 text-xs w-full ${hasError ? 'border-red-500 bg-red-50' : 'border-slate-200'} ${extra}`
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No tasks yet. Extract tasks from your SOW or add one manually.
        <div className="mt-2">
          <button onClick={addRow} className="text-blue-600 underline text-xs">+ Add task</button>
        </div>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-slate-100 text-slate-600 text-left">
            {['Task Name *', 'Description *', 'Assignee', 'Hours *', 'Billing *',
              'Milestone', 'Priority', 'Dependencies', 'Start Date', 'End Date', ''].map((h) => (
              <th key={h} className="p-2 border border-slate-200 min-w-[80px]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.row_id} className="hover:bg-slate-50">
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'task_name')} value={task.task_name}
                  onChange={(e) => update(task.row_id, { task_name: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'description')} value={task.description}
                  onChange={(e) => update(task.row_id, { description: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'assignee_name')}
                  value={task.assignee_name ?? ''}
                  onChange={(e) => update(task.row_id, { assignee_name: e.target.value || null })}>
                  <option value="">— unassigned —</option>
                  {members.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                <input type="number" step="0.5" min="0.5" max="999"
                  className={cellClass(task.row_id, 'estimated_hours', task._hours_defaulted ? 'bg-amber-50' : '')}
                  value={task.estimated_hours}
                  title={task._hours_defaulted ? 'Defaulted to 1.0 by AI — please verify' : undefined}
                  onChange={(e) => update(task.row_id, {
                    estimated_hours: parseFloat(e.target.value),
                    _hours_defaulted: false,
                  })} />
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'billing_type')}
                  value={task.billing_type}
                  onChange={(e) => update(task.row_id, { billing_type: e.target.value as BillingType })}>
                  {BILLING_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                {/* datalist provides autocomplete from fetched milestones */}
                <input list={`ms-${task.row_id}`}
                  className={cellClass(task.row_id, 'sprint_milestone')}
                  value={task.sprint_milestone ?? ''}
                  placeholder="optional"
                  onChange={(e) => update(task.row_id, { sprint_milestone: e.target.value || null })} />
                <datalist id={`ms-${task.row_id}`}>
                  {milestones.map((m) => <option key={m.id} value={m.name} />)}
                </datalist>
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'priority')}
                  value={task.priority ?? ''}
                  onChange={(e) => update(task.row_id, { priority: (e.target.value as Priority) || null })}>
                  <option value="">—</option>
                  {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'dependencies')}
                  value={task.dependencies.join(', ')}
                  placeholder="Task A, Task B"
                  onChange={(e) => update(task.row_id, {
                    dependencies: e.target.value
                      ? e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                      : [],
                  })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input type="date" className={cellClass(task.row_id, 'start_date')}
                  value={task.start_date ?? ''}
                  onChange={(e) => update(task.row_id, { start_date: e.target.value || null })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input type="date" className={cellClass(task.row_id, 'end_date')}
                  value={task.end_date ?? ''}
                  min={task.start_date ?? undefined}
                  onChange={(e) => update(task.row_id, { end_date: e.target.value || null })} />
              </td>
              <td className="p-1 border border-slate-200 text-center">
                <button onClick={() => deleteRow(task.row_id)}
                  className="text-red-400 hover:text-red-600 font-bold" title="Delete row">×</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={addRow} className="mt-2 text-blue-600 underline text-xs">+ Add task</button>
    </div>
  )
}
