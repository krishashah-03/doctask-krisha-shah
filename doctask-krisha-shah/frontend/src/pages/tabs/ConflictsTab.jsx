import { useCallback, useEffect, useState } from 'react'
import { get } from '../../api/client'
import ConflictCard from '../../components/ConflictCard'
import InfoNote from '../../components/InfoNote'

export default function ConflictsTab({ pileId, refreshKey, onMutate }) {
  const [conflicts, setConflicts] = useState(null)
  const [factsById, setFactsById] = useState({})
  const [documentsById, setDocumentsById] = useState({})
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    Promise.all([
      get(`/piles/${pileId}/conflicts`),
      get(`/piles/${pileId}/facts`),
      get(`/piles/${pileId}/documents`),
    ])
      .then(([conflictList, facts, documents]) => {
        setConflicts(conflictList)
        setFactsById(Object.fromEntries(facts.map((fact) => [fact.id, fact])))
        setDocumentsById(Object.fromEntries(documents.map((doc) => [doc.id, doc])))
      })
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh, refreshKey])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (conflicts === null) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div className="flex flex-col gap-4">
      <InfoNote>
        <p>
          A <strong>conflict</strong> is two facts with the same key but different values, from two different
          documents (e.g. the contract says 45-day payment terms, the amendment says 60). Both facts are
          withheld from the deliverable until you approve one reading here — that's why the Deliverable tab
          can show 0 included facts even after a successful run.
        </p>
      </InfoNote>
      {conflicts.length === 0 ? (
        <p className="text-sm text-slate-500">
          No conflicts detected — either the documents agree, or the pipeline hasn't run yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {conflicts.map((conflict) => (
            <ConflictCard
              key={conflict.id}
              conflict={conflict}
              factsById={factsById}
              documentsById={documentsById}
              onDecided={() => {
                refresh()
                onMutate?.()
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
