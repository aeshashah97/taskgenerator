import React, { useState, useEffect, useRef, useMemo } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { Task, BillingType, Priority, ZohoMember } from '../types/task'
import { validateTasksForPush } from '../utils/validation'

interface Props {
  tasks: Task[]
  members: ZohoMember[]
  onChange: (tasks: Task[]) => void  // receives full updated task array
}

const BILLING_OPTIONS: BillingType[] = ['billable', 'non-billable']
const PRIORITY_OPTIONS: Priority[] = ['high', 'medium', 'low']

const CSV_COLUMNS: (keyof Task)[] = [
  'task_name', 'description', 'assignee_names', 'estimated_hours',
  'billing_type', 'priority', 'start_date', 'end_date',
]

function csvField(col: keyof Task, value: unknown): string {
  if (col === 'assignee_names') {
    const names = (value as string[])
    const joined = names.join(';')
    if (joined.includes('"') || joined.includes('\n')) {
      return '"' + joined.replace(/"/g, '""') + '"'
    }
    return joined
  }
  if (value === null || value === undefined) return ''
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

function buildCsv(tasks: Task[]): string {
  const header = CSV_COLUMNS.join(',')
  const rows = tasks.map(t => CSV_COLUMNS.map(col => csvField(col, t[col])).join(','))
  return [header, ...rows].join('\r\n')
}

function downloadCsv(content: string, filename: string): void {
  const blob = new Blob(['\uFEFF', content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function emptyTask(): Task {
  return {
    row_id: uuidv4(),
    task_name: '',
    description: '',
    assignee_names: [],
    estimated_hours: null,
    billing_type: 'billable',
    priority: null,
    dependencies: [],
    start_date: null,
    end_date: null,
  }
}

interface AssigneeMultiSelectProps {
  value: string[]
  members: ZohoMember[]
  onChange: (names: string[]) => void
  hasError?: boolean
}

function AssigneeMultiSelect({ value, members, onChange, hasError }: AssigneeMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  function toggle(name: string) {
    if (value.includes(name)) {
      onChange(value.filter(n => n !== name))
    } else {
      onChange([...value, name])
    }
  }

  const displayText = value.length > 0 ? value.join(', ') : '— unassigned —'
  const borderClass = hasError ? 'border-red-500 bg-red-50' : 'border-slate-200'

  return (
    <div ref={ref} className="relative">
      <div
        className={`border rounded px-1 py-0.5 text-xs w-full cursor-pointer truncate ${borderClass}`}
        onClick={() => setOpen(o => !o)}
        title={value.length > 0 ? value.join(', ') : undefined}
      >
        {displayText}
      </div>
      {open && (
        <div className="absolute z-10 top-full left-0 mt-0.5 bg-white border border-slate-200 rounded shadow-md min-w-[160px] max-h-48 overflow-y-auto">
          {members.length === 0 && (
            <div className="px-2 py-1 text-xs text-slate-400">No members</div>
          )}
          {members.map(m => (
            <label key={m.id} className="flex items-center gap-1.5 px-2 py-1 hover:bg-slate-50 cursor-pointer text-xs">
              <input
                type="checkbox"
                checked={value.includes(m.name)}
                onChange={() => toggle(m.name)}
              />
              {m.name}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

export function TaskTable({ tasks, members, onChange }: Props) {
  const errors = useMemo(() => validateTasksForPush(tasks), [tasks])
  const errorMap = useMemo(
    () => Object.fromEntries(errors.map((e) => [e.row_id, new Set(e.fields)])),
    [errors]
  )

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkAssignees, setBulkAssignees] = useState<string[]>([])
  const [bulkPriority, setBulkPriority] = useState('')
  const [bulkBilling, setBulkBilling] = useState('')
  const selectAllRef = useRef<HTMLInputElement>(null)

  // Prune selectedIds to only IDs still present in tasks
  useEffect(() => {
    setSelectedIds(prev => {
      const next = new Set([...prev].filter(id => tasks.some(t => t.row_id === id)))
      return next.size === prev.size ? prev : next
    })
  }, [tasks])

  const allSelected = selectedIds.size === tasks.length && tasks.length > 0
  const someSelected = selectedIds.size > 0 && !allSelected

  // Sync indeterminate state on the select-all checkbox ref
  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected
    }
  }, [someSelected])

  function update(row_id: string, patch: Partial<Task>) {
    onChange(tasks.map((t) => (t.row_id === row_id ? { ...t, ...patch } : t)))
  }

  function addRow() { onChange([...tasks, emptyTask()]) }
  function deleteRow(row_id: string) { onChange(tasks.filter((t) => t.row_id !== row_id)) }

  function toggleRow(row_id: string) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(row_id) ? next.delete(row_id) : next.add(row_id)
      return next
    })
  }

  function handleSelectAll(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.checked) {
      setSelectedIds(new Set(tasks.map(t => t.row_id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  function bulkUpdate(patch: Partial<Task>) {
    onChange(tasks.map(t => selectedIds.has(t.row_id) ? { ...t, ...patch } : t))
  }

  function applyBulkAssignees() {
    if (bulkAssignees.length === 0) return
    onChange(tasks.map(t =>
      selectedIds.has(t.row_id)
        ? { ...t, assignee_names: [...new Set([...t.assignee_names, ...bulkAssignees])] }
        : t
    ))
    setBulkAssignees([])
  }

  function cellClass(row_id: string, field: string, extra = '') {
    const hasError = errorMap[row_id]?.has(field)
    return `border rounded px-1 py-0.5 text-xs w-full ${hasError ? 'border-red-500 bg-red-50' : 'border-slate-200'} ${extra}`
  }


  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No tasks yet. Extract tasks from your SOW or add one manually.
        <div className="mt-2">
          <button onClick={addRow} className="text-indigo-600 hover:text-indigo-800 underline text-xs">+ Add task</button>
        </div>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-lg mb-2">
          <span className="text-sm font-medium text-indigo-700">{selectedIds.size} selected</span>

          <AssigneeMultiSelect
            value={bulkAssignees}
            members={members}
            onChange={(names) => setBulkAssignees(names)}
          />
          <button
            onClick={applyBulkAssignees}
            className="text-xs text-slate-500 hover:text-slate-700 underline"
          >
            Apply
          </button>

          <select
            className="border rounded px-1 py-0.5 text-xs border-slate-200"
            value={bulkPriority}
            onChange={(e) => {
              if (!e.target.value) return
              bulkUpdate({ priority: e.target.value as Priority })
              setBulkPriority('')
            }}
          >
            <option value="">Set priority…</option>
            {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>

          <select
            className="border rounded px-1 py-0.5 text-xs border-slate-200"
            value={bulkBilling}
            onChange={(e) => {
              if (!e.target.value) return
              bulkUpdate({ billing_type: e.target.value as BillingType })
              setBulkBilling('')
            }}
          >
            <option value="">Set billing…</option>
            {BILLING_OPTIONS.map(b => <option key={b} value={b}>{b}</option>)}
          </select>

          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-xs text-slate-500 hover:text-slate-700 underline"
          >
            Deselect all
          </button>
        </div>
      )}
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-slate-100 text-slate-600 text-left">
            <th className="p-2 border border-slate-200 w-8">
              <input
                type="checkbox"
                ref={selectAllRef}
                checked={allSelected}
                onChange={handleSelectAll}
              />
            </th>
            {['Task Name *', 'Description *', 'Assignee', 'Hours *', 'Billing *',
              'Priority', 'Start Date', 'End Date', ''].map((h) => (
              <th key={h} className="p-2 border border-slate-200 min-w-[80px]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.row_id} className={selectedIds.has(task.row_id) ? 'bg-indigo-100' : 'hover:bg-indigo-50 transition-colors'}>
              <td className="p-1 border border-slate-200 text-center">
                <input
                  type="checkbox"
                  checked={selectedIds.has(task.row_id)}
                  onChange={() => toggleRow(task.row_id)}
                />
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'task_name')} value={task.task_name}
                  onChange={(e) => update(task.row_id, { task_name: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'description')} value={task.description}
                  onChange={(e) => update(task.row_id, { description: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <AssigneeMultiSelect
                  value={task.assignee_names}
                  members={members}
                  onChange={(names) => update(task.row_id, { assignee_names: names })}
                  hasError={errorMap[task.row_id]?.has('assignee_names')}
                />
              </td>
              <td className="p-1 border border-slate-200">
                <input type="number" step="0.5" min="0.5" max="999"
                  className={cellClass(task.row_id, 'estimated_hours')}
                  value={task.estimated_hours ?? ''}
                  placeholder="hours"
                  onChange={(e) => update(task.row_id, {
                    estimated_hours: e.target.value ? parseFloat(e.target.value) : null,
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
                <select
                  className={cellClass(task.row_id, 'priority') + ` ${
                    task.priority === 'high' ? 'text-red-600' :
                    task.priority === 'medium' ? 'text-amber-600' :
                    task.priority === 'low' ? 'text-green-600' : ''
                  }`}
                  value={task.priority ?? ''}
                  onChange={(e) => update(task.row_id, { priority: (e.target.value as Priority) || null })}>
                  <option value="">—</option>
                  {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
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
      <div className="flex items-center gap-4 mt-2">
        <button onClick={addRow} className="text-indigo-600 hover:text-indigo-800 underline text-xs font-medium">
          + Add task
        </button>
        <button
          onClick={() => downloadCsv(buildCsv(tasks), 'tasks.csv')}
          disabled={tasks.length === 0} // defensive: component early-returns on empty tasks, but guard kept for safety
          className="text-indigo-600 hover:text-indigo-800 underline text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Export CSV
        </button>
      </div>
    </div>
  )
}
