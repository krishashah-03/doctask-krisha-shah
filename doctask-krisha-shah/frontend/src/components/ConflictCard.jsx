import { FiAlertTriangle } from 'react-icons/fi'
import StatusBadge from './StatusBadge'
import ReviewDecisionButtons from './ReviewDecisionButtons'

export default function ConflictCard({ conflict, onDecided }) {
  const detail = conflict.detail ?? conflict
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2">
          <FiAlertTriangle className="mt-0.5 shrink-0 text-amber-500" />
          <div>
            <p className="font-medium text-slate-900">{detail.fact_key ?? conflict.description}</p>
            <p className="mt-1 text-sm text-slate-600">{conflict.description}</p>
          </div>
        </div>
        <StatusBadge status={conflict.status} />
      </div>
      {conflict.status === 'pending' && (
        <div className="mt-3 flex justify-end">
          <ReviewDecisionButtons
            itemType="conflict"
            itemId={conflict.item_id ?? conflict.id}
            onDecided={onDecided}
          />
        </div>
      )}
    </div>
  )
}
