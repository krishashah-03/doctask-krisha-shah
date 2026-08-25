import { FiLoader } from 'react-icons/fi'
import { TERMINAL_STATUSES } from '../lib/runStages'
import StatusBadge from './StatusBadge'

// Presentational only — PileDetail owns the polling (via usePolling) so the
// status badge and the PipelineStages stepper share one fetched run object
// instead of each polling /runs/:id separately.
export default function RunStatusBadge({ run, error }) {
  if (error) return <span className="text-sm text-red-600">Failed to load run status.</span>
  if (!run) return null

  const isRunning = !TERMINAL_STATUSES.has(run.status)

  return (
    <div className="flex items-center gap-2 text-sm">
      {isRunning && <FiLoader className="animate-spin text-blue-500" />}
      <StatusBadge status={run.status} />
    </div>
  )
}
