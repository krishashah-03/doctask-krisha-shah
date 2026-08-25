import { useCallback, useEffect, useState } from 'react'
import { get } from '../api/client'
import ConflictCard from '../components/ConflictCard'
import FindingCard from '../components/FindingCard'
import InfoNote from '../components/InfoNote'

export default function PendingReview() {
  const [piles, setPiles] = useState(null)
  const [selectedPileId, setSelectedPileId] = useState('')
  const [items, setItems] = useState(null)
  const [factsById, setFactsById] = useState({})
  const [documentsById, setDocumentsById] = useState({})
  const [rulesById, setRulesById] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    get('/piles')
      .then((list) => {
        setPiles(list)
        if (list.length > 0) setSelectedPileId(list[0].id)
      })
      .catch((err) => setError(err.message))
  }, [])

  const refresh = useCallback(() => {
    if (!selectedPileId) return
    get(`/piles/${selectedPileId}/pending-review`)
      .then(setItems)
      .catch((err) => setError(err.message))
    Promise.all([
      get(`/piles/${selectedPileId}/facts`),
      get(`/piles/${selectedPileId}/documents`),
      get(`/piles/${selectedPileId}/rules`),
    ])
      .then(([facts, documents, rules]) => {
        setFactsById(Object.fromEntries(facts.map((fact) => [fact.id, fact])))
        setDocumentsById(Object.fromEntries(documents.map((doc) => [doc.id, doc])))
        setRulesById(Object.fromEntries(rules.map((rule) => [rule.id, rule])))
      })
      .catch((err) => setError(err.message))
  }, [selectedPileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Pending Review</h1>
        {piles && piles.length > 0 && (
          <select
            value={selectedPileId}
            onChange={(event) => setSelectedPileId(event.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {piles.map((pile) => (
              <option key={pile.id} value={pile.id}>
                {pile.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <InfoNote>
        <p>
          This is the human gate: every conflict and finding below is pending approval or rejection before it
          affects the deliverable. Nothing here is auto-resolved — approve or reject each one individually,
          and rejecting one doesn't discard the rest.
        </p>
      </InfoNote>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {piles === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : piles.length === 0 ? (
        <p className="text-sm text-slate-500">No piles yet.</p>
      ) : items === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">Nothing pending review — you're all caught up.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) =>
            item.item_type === 'conflict' ? (
              <ConflictCard
                key={item.item_id}
                conflict={item}
                factsById={factsById}
                documentsById={documentsById}
                onDecided={refresh}
              />
            ) : (
              <FindingCard key={item.item_id} finding={item} rulesById={rulesById} onDecided={refresh} />
            )
          )}
        </div>
      )}
    </div>
  )
}
