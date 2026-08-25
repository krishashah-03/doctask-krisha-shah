import { useCallback, useEffect, useState } from 'react'
import { get } from '../../api/client'
import FindingCard from '../../components/FindingCard'
import InfoNote from '../../components/InfoNote'

export default function FindingsTab({ pileId, refreshKey, onMutate }) {
  const [findings, setFindings] = useState(null)
  const [rulesById, setRulesById] = useState({})
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    Promise.all([get(`/piles/${pileId}/findings`), get(`/piles/${pileId}/rules`)])
      .then(([findingList, rules]) => {
        setFindings(findingList)
        setRulesById(Object.fromEntries(rules.map((rule) => [rule.id, rule])))
      })
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh, refreshKey])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (findings === null) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div className="flex flex-col gap-4">
      <InfoNote>
        <p>
          A <strong>finding</strong> is a rule violation the AI spotted while checking extracted facts against
          the rules you defined in the Rules tab — e.g. a payment term that exceeds your compliance ceiling.
          Zero findings is a genuine, valid outcome, not a sign nothing ran; check the Rules tab to confirm
          rules exist and have actually been examined.
        </p>
      </InfoNote>
      {findings.length === 0 ? (
        <p className="text-sm text-slate-500">
          No findings — either every rule passed cleanly, or no rules have been defined/examined yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {findings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              rulesById={rulesById}
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
