import { FiLoader } from 'react-icons/fi'
import { get } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import StatusBadge from './StatusBadge'

const TERMINAL_STATUSES = new Set(['completed', 'failed'])

export default function RunStatusBadge({ runId, onSettled }) {
  const { data: run, error } = usePolling(() => get(`/runs/${runId}`), {
    active: Boolean(runId),
    intervalMs: 2000,
    isDone: (result) => {
      const done = TERMINAL_STATUSES.has(result?.status)
      if (done) onSettled?.(result)
      return done
    },
  })

  if (!runId) return null
  if (error) return <span className="text-sm text-red-600">Failed to load run status.</span>
  if (!run) return <span className="text-sm text-slate-500">Starting run…</span>

  const isRunning = !TERMINAL_STATUSES.has(run.status)

  return (
    <div className="flex items-center gap-2 text-sm">
      {isRunning && <FiLoader className="animate-spin text-blue-500" />}
      <StatusBadge status={run.status} />
      {isRunning && run.current_stage && (
        <span className="text-slate-500">stage: {run.current_stage}</span>
      )}
    </div>
  )
}
