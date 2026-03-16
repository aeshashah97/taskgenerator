import { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ProjectSelector } from './components/ProjectSelector'
import { InputPanel } from './components/InputPanel'
import { TaskTable } from './components/TaskTable'
import { FeedbackPanel } from './components/FeedbackPanel'
import { Button } from './components/ui/button'
import { useProjectMembers } from './hooks/useProjectMembers'
import { useProjectMilestones } from './hooks/useProjectMilestones'
import { extractTasks, pushTasks } from './api/client'
import { isPushReady } from './utils/validation'
import { HOURS_SENTINEL } from './types/task'
import type { Task, PushTaskResult } from './types/task'

export default function App() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [sowText, setSowText] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [pushing, setPushing] = useState(false)
  const [pushResults, setPushResults] = useState<PushTaskResult[]>([])

  const { members, loading: membersLoading } = useProjectMembers(selectedProject)
  const { milestones } = useProjectMilestones(selectedProject)

  function handleProjectChange(projectId: string) {
    setSelectedProject(projectId)
    setTasks([])
    setPushResults([])
    setExtractError(null)
  }

  async function handleExtract() {
    if (!sowText.trim() || !selectedProject) return
    setExtracting(true)
    setExtractError(null)
    setPushResults([])
    try {
      const rawTasks = await extractTasks({
        sow_text: sowText,
        team_members: members.map((m) => m.name),
      })
      const tasksWithIds: Task[] = rawTasks.map((t) => ({
        ...t,
        row_id: uuidv4(),
        dependencies: t.dependencies ?? [],
        // Mark hours as defaulted when AI returned the sentinel value (1 or 1.0)
        _hours_defaulted: t.estimated_hours === HOURS_SENTINEL,
      }))
      setTasks(tasksWithIds)
    } catch (e: unknown) {
      const err = e as { body?: { error?: string; raw_response?: string }; message?: string }
      if (err.body?.error === 'parse_failed') {
        setExtractError(`AI could not parse the SOW. Raw response: ${err.body.raw_response}`)
      } else {
        setExtractError(err.message ?? 'Extraction failed')
      }
    } finally {
      setExtracting(false)
    }
  }

  async function handlePush() {
    if (!selectedProject || !isPushReady(tasks)) return
    setPushing(true)
    setPushResults([])
    try {
      const response = await pushTasks({ project_id: selectedProject, tasks })
      setPushResults(response.results)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Push failed'
      setPushResults([{
        row_id: 'global-error',
        task_name: 'All tasks',
        status: 'failed',
        zoho_task_id: null,
        warnings: [],
        error: message,
      }])
    } finally {
      setPushing(false)
    }
  }

  const canExtract = !!selectedProject && sowText.trim().length > 0 && sowText.length <= 50_000 && !extracting
  const canPush = isPushReady(tasks) && !pushing && !extracting

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">SOW Task Generator</h1>
        <p className="text-sm text-slate-500">
          Extract tasks from your SOW and push them directly to Zoho Projects
        </p>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-6 flex flex-col gap-6">
        <section className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
            1. Select Zoho Project
          </h2>
          <ProjectSelector value={selectedProject} onChange={handleProjectChange} />
        </section>

        <section className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
            2. Provide SOW / WBS
          </h2>
          <InputPanel onSowReady={setSowText} disabled={!selectedProject} />
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={handleExtract} disabled={!canExtract}>
              {extracting ? 'Extracting…' : 'Extract Tasks'}
            </Button>
            {membersLoading && (
              <span className="text-xs text-slate-400">Loading team members…</span>
            )}
          </div>
          {extractError && <p className="mt-2 text-sm text-red-600">{extractError}</p>}
        </section>

        {tasks.length > 0 && (
          <section className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
              3. Review &amp; Edit Tasks ({tasks.length})
            </h2>
            <TaskTable tasks={tasks} members={members} milestones={milestones} onChange={setTasks} />
            <div className="mt-4">
              <Button onClick={handlePush} disabled={!canPush}>
                {pushing
                  ? 'Pushing to Zoho…'
                  : `Push ${tasks.length} Task${tasks.length !== 1 ? 's' : ''} to Zoho`}
              </Button>
              {!canPush && tasks.length > 0 && (
                <p className="mt-1 text-xs text-slate-400">Fix highlighted fields before pushing.</p>
              )}
            </div>
          </section>
        )}

        {pushResults.length > 0 && (
          <section className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
              4. Push Results
            </h2>
            <FeedbackPanel results={pushResults} />
          </section>
        )}
      </main>
    </div>
  )
}
