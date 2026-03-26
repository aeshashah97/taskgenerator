import { useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ProjectSelector } from './components/ProjectSelector'
import { InputPanel } from './components/InputPanel'
import { TaskTable } from './components/TaskTable'
import { FeedbackPanel } from './components/FeedbackPanel'
import { StepperBar } from './components/StepperBar'
import { StepCard } from './components/StepCard'
import { useProjectMembers } from './hooks/useProjectMembers'
import { extractTasks, pushTasks } from './api/client'
import { isPushReady } from './utils/validation'
import type { Task, PushTaskResult } from './types/task'

export default function App() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [selectedProjectName, setSelectedProjectName] = useState<string | null>(null)
  const [sowText, setSowText] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [pushing, setPushing] = useState(false)
  const [pushResults, setPushResults] = useState<PushTaskResult[]>([])
  const [activeStep, setActiveStep] = useState<number>(1)

  const { members, loading: membersLoading } = useProjectMembers(selectedProject)

  useEffect(() => { if (selectedProject) setActiveStep(prev => prev === 1 ? 2 : prev) }, [selectedProject])
  useEffect(() => { if (tasks.length > 0) setActiveStep(prev => prev === 2 ? 3 : prev) }, [tasks])
  useEffect(() => { if (pushResults.length > 0) setActiveStep(prev => prev === 3 ? 4 : prev) }, [pushResults])

  function handleProjectChange(projectId: string, projectName: string) {
    setSelectedProject(projectId)
    setSelectedProjectName(projectName)
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
        assignee_name: null,
        dependencies: t.dependencies ?? [],
        estimated_hours: t.estimated_hours ?? null,
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
      <header className="bg-indigo-600 px-6 py-4">
        <h1 className="text-2xl font-bold text-white">SOW Task Generator</h1>
        <p className="text-sm text-indigo-200">Extract tasks from your SOW and push them directly to Zoho Projects</p>
      </header>

      <StepperBar activeStep={activeStep} />

      <main className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4">

        <StepCard
          step={1}
          title="Select Zoho Project"
          activeStep={activeStep}
          summary={selectedProjectName ? `Project: ${selectedProjectName}` : undefined}
          onEdit={() => setActiveStep(1)}
        >
          <ProjectSelector value={selectedProject} onChange={handleProjectChange} />
        </StepCard>

        <StepCard
          step={2}
          title="Provide SOW / WBS"
          activeStep={activeStep}
          summary={`${tasks.length} task${tasks.length !== 1 ? 's' : ''} extracted`}
          onEdit={() => setActiveStep(2)}
        >
          <InputPanel onSowReady={setSowText} disabled={!selectedProject} />
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleExtract}
              disabled={!canExtract}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg px-5 py-2 text-sm transition-colors"
            >
              {extracting ? 'Analysing with AI…' : 'Extract Tasks'}
            </button>
            {membersLoading && <span className="text-xs text-slate-400">Loading team members…</span>}
          </div>
          {extractError && <p className="mt-2 text-sm text-red-600">{extractError}</p>}
        </StepCard>

        <StepCard
          step={3}
          title={`Review & Edit Tasks${tasks.length > 0 ? ` (${tasks.length})` : ''}`}
          activeStep={activeStep}
          summary="Push complete"
          onEdit={() => setActiveStep(3)}
        >
          <TaskTable tasks={tasks} members={members} onChange={setTasks} />
          <div className="mt-4 flex items-center justify-between">
            <div>
              {!canPush && tasks.length > 0 && (
                <p className="text-xs text-slate-400">Fix highlighted fields before pushing.</p>
              )}
            </div>
            <button
              onClick={handlePush}
              disabled={!canPush}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg px-5 py-2 text-sm transition-colors"
            >
              {pushing ? 'Pushing to Zoho…' : `Push ${tasks.length} Task${tasks.length !== 1 ? 's' : ''} to Zoho`}
            </button>
          </div>
        </StepCard>

        <StepCard
          step={4}
          title="Push Results"
          activeStep={activeStep}
        >
          <FeedbackPanel results={pushResults} />
        </StepCard>

      </main>
    </div>
  )
}
