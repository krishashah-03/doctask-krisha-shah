import { FiCheck, FiLoader } from 'react-icons/fi'
import { PIPELINE_STEPS, stepIndexFor } from '../lib/runStages'

// Shows the pipeline as the 4 stages it actually moves through, with the
// current one highlighted — replaces a bare spinner with something that
// answers "where is it right now, and what already finished".
export default function PipelineStages({ run }) {
  if (!run) return null
  const activeIndex = stepIndexFor(run.current_stage)
  const isDone = run.status === 'completed'
  const isFailed = run.status === 'failed'

  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2">
      {PIPELINE_STEPS.map((step, index) => {
        const stepIsFailure = isFailed && index === activeIndex
        const stepIsComplete = isDone || index < activeIndex
        const stepIsCurrent = !isDone && !isFailed && index === activeIndex

        const classes = stepIsFailure
          ? 'bg-red-100 text-red-700'
          : stepIsComplete
            ? 'bg-green-100 text-green-700'
            : stepIsCurrent
              ? 'bg-blue-100 text-blue-700'
              : 'bg-slate-100 text-slate-400'

        return (
          <div key={step.key} className="flex items-center gap-1">
            <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${classes}`}>
              {stepIsComplete ? (
                <FiCheck size={12} />
              ) : stepIsCurrent ? (
                <FiLoader className="animate-spin" size={12} />
              ) : null}
              {step.label}
            </span>
            {index < PIPELINE_STEPS.length - 1 && <div className="h-px w-3 bg-slate-200" />}
          </div>
        )
      })}
    </div>
  )
}
