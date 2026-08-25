import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { FiPlay } from 'react-icons/fi'
import { get, post } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { TERMINAL_STATUSES, lastRunStorageKey } from '../lib/runStages'
import RunStatusBadge from '../components/RunStatusBadge'
import PipelineStages from '../components/PipelineStages'
import DocumentsTab from './tabs/DocumentsTab'
import FactsTab from './tabs/FactsTab'
import ConflictsTab from './tabs/ConflictsTab'
import FindingsTab from './tabs/FindingsTab'
import DeliverableTab from './tabs/DeliverableTab'
import RulesTab from './tabs/RulesTab'

const TABS = ['Documents', 'Facts', 'Conflicts', 'Findings', 'Deliverable', 'Rules']

export default function PileDetail() {
  const { pileId } = useParams()
  const [pile, setPile] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('Documents')
  const [runId, setRunId] = useState(() => localStorage.getItem(lastRunStorageKey(pileId)))
  const [refreshKey, setRefreshKey] = useState(0)
  const [counts, setCounts] = useState({ documents: null, facts: null, pendingConflicts: null, pendingFindings: null })

  const refreshCounts = useCallback(() => {
    Promise.all([
      get(`/piles/${pileId}/documents`),
      get(`/piles/${pileId}/facts`),
      get(`/piles/${pileId}/conflicts`),
      get(`/piles/${pileId}/findings`),
    ])
      .then(([documents, facts, conflicts, findings]) => {
        setCounts({
          documents: documents.length,
          facts: facts.length,
          pendingConflicts: conflicts.filter((c) => c.status === 'pending').length,
          pendingFindings: findings.filter((f) => f.status === 'pending').length,
        })
      })
      .catch(() => {})
  }, [pileId])

  // A run can change facts/conflicts/findings/the draft all at once, so
  // once it settles, bump refreshKey (every tab re-fetches) right from the
  // poll's own completion callback rather than a derived render effect.
  const { data: run, error: runError } = usePolling(() => get(`/runs/${runId}`), {
    active: Boolean(runId),
    intervalMs: 2000,
    isDone: (result) => {
      const done = TERMINAL_STATUSES.has(result?.status)
      if (done) {
        setRefreshKey((key) => key + 1)
        refreshCounts()
      }
      return done
    },
  })

  useEffect(() => {
    get(`/piles/${pileId}`)
      .then(setPile)
      .catch((err) => setError(err.message))
    refreshCounts()
  }, [pileId, refreshCounts])

  function handleMutate() {
    setRefreshKey((key) => key + 1)
    refreshCounts()
  }

  async function handleRunPipeline() {
    setError(null)
    try {
      const run = await post(`/piles/${pileId}/run`)
      setRunId(run.id)
      localStorage.setItem(lastRunStorageKey(pileId), run.id)
    } catch (err) {
      setError(err.message)
    }
  }

  if (error && !pile) return <p className="text-sm text-red-600">{error}</p>
  if (!pile) return <p className="text-sm text-slate-500">Loading…</p>

  const tabCount = {
    Documents: counts.documents,
    Facts: counts.facts,
    Conflicts: counts.pendingConflicts,
    Findings: counts.pendingFindings,
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{pile.name}</h1>
          <p className="text-sm text-slate-500">{pile.domain}</p>
        </div>
        <div className="flex items-center gap-3">
          <RunStatusBadge run={run} error={runError} />
          <button
            type="button"
            onClick={handleRunPipeline}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            <FiPlay /> Run Pipeline
          </button>
        </div>
      </div>

      {run && <PipelineStages run={run} />}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {TABS.map((tab) => {
          const count = tabCount[tab]
          const isConflictOrFinding = tab === 'Conflicts' || tab === 'Findings'
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 whitespace-nowrap px-3 py-2 text-sm font-medium ${
                activeTab === tab
                  ? 'border-b-2 border-slate-900 text-slate-900'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab}
              {count != null && count > 0 && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                    isConflictOrFinding ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {activeTab === 'Documents' && <DocumentsTab pileId={pileId} onMutate={handleMutate} />}
      {activeTab === 'Facts' && <FactsTab pileId={pileId} refreshKey={refreshKey} />}
      {activeTab === 'Conflicts' && <ConflictsTab pileId={pileId} refreshKey={refreshKey} onMutate={handleMutate} />}
      {activeTab === 'Findings' && <FindingsTab pileId={pileId} refreshKey={refreshKey} onMutate={handleMutate} />}
      {activeTab === 'Deliverable' && <DeliverableTab pileId={pileId} refreshKey={refreshKey} onMutate={handleMutate} />}
      {activeTab === 'Rules' && <RulesTab pileId={pileId} refreshKey={refreshKey} onMutate={handleMutate} />}
    </div>
  )
}
