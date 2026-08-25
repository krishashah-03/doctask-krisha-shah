import { FiAlertTriangle } from 'react-icons/fi'
import StatusBadge from './StatusBadge'
import ReviewDecisionButtons from './ReviewDecisionButtons'

function FactSide({ fact, documentsById }) {
  if (!fact) return <span className="text-slate-400">unknown fact</span>
  const doc = documentsById?.[fact.document_id]
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
      <p className="font-medium text-slate-900">{fact.fact_value}</p>
      <p className="text-xs text-slate-500">from {doc?.original_filename ?? fact.document_id}</p>
    </div>
  )
}

// Accepts either the direct GET /piles/:id/conflicts shape (ConflictOut) or
// the merged GET /piles/:id/pending-review shape (item_id + nested detail)
// used by the PendingReview page — normalized once here instead of forcing
// every caller to reshape it first.
export default function ConflictCard({ conflict, factsById, documentsById, onDecided }) {
  const detail = conflict.detail ?? conflict
  const id = conflict.item_id ?? conflict.id
  const runId = detail.run_id ?? conflict.run_id ?? null
  const factKey = detail.fact_key ?? conflict.fact_key
  const factA = factsById?.[detail.fact_id_a]
  const factB = factsById?.[detail.fact_id_b]

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2">
          <FiAlertTriangle className="mt-0.5 shrink-0 text-amber-500" />
          <div>
            <p className="font-medium text-slate-900">Disagreement on "{factKey}"</p>
            <p className="mt-1 text-sm text-slate-600">{conflict.description}</p>
          </div>
        </div>
        <StatusBadge status={conflict.status} />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <FactSide fact={factA} documentsById={documentsById} />
        <FactSide fact={factB} documentsById={documentsById} />
      </div>

      {conflict.status === 'pending' && (
        <div className="mt-3 flex justify-end">
          <ReviewDecisionButtons itemType="conflict" itemId={id} runId={runId} onDecided={onDecided} />
        </div>
      )}
    </div>
  )
}
