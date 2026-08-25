import { useCallback, useEffect, useState } from 'react'
import { get, post } from '../../api/client'
import DiffViewer from '../../components/DiffViewer'
import DeliverableSections from '../../components/DeliverableSections'
import InfoNote from '../../components/InfoNote'

function explainExclusion(factId, factsById, conflicts) {
  const fact = factsById[factId]
  if (!fact) return 'This fact could not be found (it may have been removed).'

  const conflict = conflicts.find((c) => c.fact_id_a === factId || c.fact_id_b === factId)
  if (conflict && conflict.status === 'pending') {
    return `Part of an unresolved conflict on "${conflict.fact_key}" — approve or reject it in the Conflicts tab to include this fact.`
  }
  if (fact.superseded_by) {
    return 'Superseded by a newer fact from a later document.'
  }
  return 'Excluded from this draft for an unlisted reason — check the Conflicts tab.'
}

function FactList({ factIds, factsById, documentsById }) {
  if (factIds.length === 0) return <p className="text-xs text-slate-400">None.</p>
  return (
    <ul className="flex flex-col gap-1">
      {factIds.map((factId) => {
        const fact = factsById[factId]
        const doc = fact ? documentsById[fact.document_id] : null
        return (
          <li key={factId} className="text-xs text-slate-600">
            <span className="font-medium text-slate-800">{fact ? `${fact.fact_key}: ${fact.fact_value}` : factId}</span>
            {doc && <span className="text-slate-400"> — {doc.original_filename}</span>}
          </li>
        )
      })}
    </ul>
  )
}

function ExcludedFactList({ factIds, factsById, documentsById, conflicts }) {
  if (factIds.length === 0) return <p className="text-xs text-slate-400">None — every extracted fact is included.</p>
  return (
    <ul className="flex flex-col gap-1.5">
      {factIds.map((factId) => {
        const fact = factsById[factId]
        return (
          <li key={factId} className="text-xs text-slate-600">
            <span className="font-medium text-slate-800">
              {fact ? `${fact.fact_key}: ${fact.fact_value}` : factId}
            </span>
            {fact && <span className="text-slate-400"> — {documentsById[fact.document_id]?.original_filename}</span>}
            <div className="text-amber-700">{explainExclusion(factId, factsById, conflicts)}</div>
          </li>
        )
      })}
    </ul>
  )
}

export default function DeliverableTab({ pileId, refreshKey, onMutate }) {
  const [latest, setLatest] = useState(null)
  const [latestMissing, setLatestMissing] = useState(false)
  const [history, setHistory] = useState(null)
  const [draft, setDraft] = useState(null)
  const [expandedVersion, setExpandedVersion] = useState(null)
  const [factsById, setFactsById] = useState({})
  const [documentsById, setDocumentsById] = useState({})
  const [conflicts, setConflicts] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(() => {
    get(`/piles/${pileId}/deliverable`)
      .then((version) => {
        setLatest(version)
        setLatestMissing(false)
      })
      .catch((err) => {
        if (err.status === 404) {
          setLatest(null)
          setLatestMissing(true)
        } else {
          setError(err.message)
        }
      })
    get(`/piles/${pileId}/deliverable/history`)
      .then(setHistory)
      .catch((err) => setError(err.message))
    get(`/piles/${pileId}/deliverable/draft`)
      .then(setDraft)
      .catch((err) => {
        if (err.status === 404) setDraft(null)
        else setError(err.message)
      })
    Promise.all([get(`/piles/${pileId}/facts`), get(`/piles/${pileId}/documents`), get(`/piles/${pileId}/conflicts`)])
      .then(([facts, documents, conflictList]) => {
        setFactsById(Object.fromEntries(facts.map((fact) => [fact.id, fact])))
        setDocumentsById(Object.fromEntries(documents.map((doc) => [doc.id, doc])))
        setConflicts(conflictList)
      })
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh, refreshKey])

  async function handleGenerateDraft() {
    setBusy(true)
    setError(null)
    try {
      await post(`/piles/${pileId}/generate-deliverable`)
      refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleCommit() {
    if (!draft) return
    setBusy(true)
    setError(null)
    try {
      await post(`/piles/${pileId}/deliverable/commit`, { run_id: draft.run_id })
      setDraft(null)
      refresh()
      onMutate?.()
    } catch (err) {
      if (err.status === 409) {
        setError('Someone else just committed a newer version — refreshing.')
        refresh()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <InfoNote>
        <p>
          The <strong>deliverable</strong> is the drafted report built only from currently-trustworthy facts —
          anything tied to an unresolved conflict is held back (see the excluded list below, with reasons).
          Running the full pipeline drafts one automatically; use <strong>Generate Draft</strong> to redraft
          without re-running extraction (e.g. after resolving a conflict). A draft is never final — a person
          must <strong>Commit</strong> it before it becomes an official version.
        </p>
      </InfoNote>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium text-slate-900">Latest committed deliverable</h2>
          <button
            type="button"
            onClick={handleGenerateDraft}
            disabled={busy}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            Generate Draft
          </button>
        </div>
        {latestMissing && (
          <p className="text-sm text-slate-500">
            No deliverable has been committed yet — generate and commit a draft below, or run the pipeline.
          </p>
        )}
        {latest && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-slate-500">Version {latest.version}</p>
            <DeliverableSections sections={latest.content?.sections} factsById={factsById} documentsById={documentsById} />
          </div>
        )}
      </div>

      {draft && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Pending draft</h2>
            <button
              type="button"
              onClick={handleCommit}
              disabled={busy}
              className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Commit Draft
            </button>
          </div>

          <DeliverableSections sections={draft.sections} factsById={factsById} documentsById={documentsById} />

          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-md border border-blue-100 bg-white p-2.5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Included facts ({draft.included_fact_ids?.length ?? 0})
              </p>
              <div className="mt-1">
                <FactList factIds={draft.included_fact_ids ?? []} factsById={factsById} documentsById={documentsById} />
              </div>
            </div>
            <div className="rounded-md border border-amber-100 bg-white p-2.5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Excluded facts ({draft.excluded_fact_ids?.length ?? 0})
              </p>
              <div className="mt-1">
                <ExcludedFactList
                  factIds={draft.excluded_fact_ids ?? []}
                  factsById={factsById}
                  documentsById={documentsById}
                  conflicts={conflicts}
                />
              </div>
            </div>
          </div>

          <div className="mt-3">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
              Changes from the last committed version
            </p>
            <DiffViewer diff={draft.diff} />
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 font-medium text-slate-900">Version history</h2>
        {history === null ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : history.length === 0 ? (
          <p className="text-sm text-slate-500">No versions yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {history.map((version) => (
              <li key={version.id} className="rounded-md border border-slate-100">
                <button
                  type="button"
                  onClick={() => setExpandedVersion(expandedVersion === version.id ? null : version.id)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm"
                >
                  <span className="font-medium text-slate-900">Version {version.version}</span>
                  <span className="text-slate-400">{new Date(version.created_at).toLocaleString()}</span>
                </button>
                {expandedVersion === version.id && (
                  <div className="border-t border-slate-100 p-3">
                    <DiffViewer diff={version.diff_from_prior} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
