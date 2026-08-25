import { useEffect, useState } from 'react'
import { get } from '../../api/client'
import FactTable from '../../components/FactTable'
import InfoNote from '../../components/InfoNote'

export default function FactsTab({ pileId, refreshKey }) {
  const [facts, setFacts] = useState(null)
  const [documentsById, setDocumentsById] = useState({})
  const [factsById, setFactsById] = useState({})
  const [conflictedFactIds, setConflictedFactIds] = useState(new Set())
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      get(`/piles/${pileId}/facts`),
      get(`/piles/${pileId}/documents`),
      get(`/piles/${pileId}/conflicts`),
    ])
      .then(([factList, documents, conflicts]) => {
        setFacts(factList)
        setDocumentsById(Object.fromEntries(documents.map((doc) => [doc.id, doc])))
        setFactsById(Object.fromEntries(factList.map((fact) => [fact.id, fact])))
        const flagged = new Set()
        for (const conflict of conflicts) {
          flagged.add(conflict.fact_id_a)
          flagged.add(conflict.fact_id_b)
        }
        setConflictedFactIds(flagged)
      })
      .catch((err) => setError(err.message))
  }, [pileId, refreshKey])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (facts === null) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div className="flex flex-col gap-4">
      <InfoNote>
        <p>
          A <strong>fact</strong> is one discrete claim the AI pulled out of a document — a key/value pair
          grounded to an exact span of source text (e.g. <em>payment_term_days = 45</em>, from the contract).
        </p>
        <p>
          When two documents state different values for the same key, both facts are marked{' '}
          <span className="inline-flex items-center gap-1 font-medium text-amber-600">⚠ in conflict</span> and
          neither is used in the deliverable until you resolve it in the Conflicts tab. When a later document
          supersedes an earlier value, the older fact is dimmed as <strong>superseded</strong>.
        </p>
      </InfoNote>
      <FactTable
        facts={facts}
        documentsById={documentsById}
        factsById={factsById}
        conflictedFactIds={conflictedFactIds}
      />
    </div>
  )
}
