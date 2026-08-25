import { FiFlag } from 'react-icons/fi'
import StatusBadge from './StatusBadge'
import ReviewDecisionButtons from './ReviewDecisionButtons'

const SEVERITY_COLORS = {
  high: 'text-red-500',
  medium: 'text-amber-500',
  low: 'text-slate-400',
}

// Same dual-shape normalization as ConflictCard — see its comment.
export default function FindingCard({ finding, rulesById, onDecided }) {
  const detail = finding.detail ?? finding
  const id = finding.item_id ?? finding.id
  const runId = detail.run_id ?? finding.run_id ?? null
  const severity = detail.severity
  const rule = detail.rule_id ? rulesById?.[detail.rule_id] : null

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2">
          <FiFlag className={`mt-0.5 shrink-0 ${SEVERITY_COLORS[severity] || 'text-slate-400'}`} />
          <div>
            <p className="font-medium text-slate-900">{finding.description}</p>
            <p className="mt-1 text-xs text-slate-500">
              {rule ? `Rule: ${rule.rule_key}` : detail.rule_id ? `Rule: ${detail.rule_id}` : null}
              {severity ? ` · Severity: ${severity}` : null}
              {detail.char_start != null ? ` · chars ${detail.char_start}-${detail.char_end}` : null}
            </p>
            {rule?.description && <p className="mt-1 text-xs text-slate-400">"{rule.description}"</p>}
          </div>
        </div>
        <StatusBadge status={finding.status} />
      </div>
      {finding.status === 'pending' && (
        <div className="mt-3 flex justify-end">
          <ReviewDecisionButtons itemType="finding" itemId={id} runId={runId} onDecided={onDecided} />
        </div>
      )}
    </div>
  )
}
