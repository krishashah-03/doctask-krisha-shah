import { useState } from 'react'
import { FiCheck, FiX } from 'react-icons/fi'
import { CURRENT_USER_ID, post } from '../api/client'

export default function ReviewDecisionButtons({ itemType, itemId, runId, onDecided }) {
  const [submitting, setSubmitting] = useState(null)
  const [error, setError] = useState(null)

  async function decide(decision) {
    setSubmitting(decision)
    setError(null)
    try {
      await post('/review-decisions', {
        item_type: itemType,
        item_id: itemId,
        run_id: runId ?? null,
        decision,
        decided_by: CURRENT_USER_ID,
      })
      onDecided?.(decision)
    } catch (err) {
      setError(err.status === 409 ? 'Already decided — refreshing.' : err.message)
      onDecided?.(null)
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => decide('approved')}
          disabled={submitting !== null}
          className="inline-flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          <FiCheck /> Approve
        </button>
        <button
          type="button"
          onClick={() => decide('rejected')}
          disabled={submitting !== null}
          className="inline-flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          <FiX /> Reject
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
