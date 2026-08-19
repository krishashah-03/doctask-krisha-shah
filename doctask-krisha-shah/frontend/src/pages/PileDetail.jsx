import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { FiPlay } from 'react-icons/fi'
import { get, post } from '../api/client'
import DocumentUpload from '../components/DocumentUpload'
import FactTable from '../components/FactTable'
import ConflictCard from '../components/ConflictCard'
import FindingCard from '../components/FindingCard'
import RuleForm from '../components/RuleForm'
import DiffViewer from '../components/DiffViewer'
import StatusBadge from '../components/StatusBadge'
import RunStatusBadge from '../components/RunStatusBadge'

const TABS = ['Documents', 'Facts', 'Conflicts', 'Findings', 'Deliverable', 'Rules']

export default function PileDetail() {
  const { pileId } = useParams()
  const [pile, setPile] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('Documents')
  const [runId, setRunId] = useState(null)

  useEffect(() => {
    get(`/piles/${pileId}`)
      .then(setPile)
      .catch((err) => setError(err.message))
  }, [pileId])

  async function handleRunPipeline() {
    setError(null)
    try {
      const run = await post(`/piles/${pileId}/run`)
      setRunId(run.id)
    } catch (err) {
      setError(err.message)
    }
  }

  if (error && !pile) return <p className="text-sm text-red-600">{error}</p>
  if (!pile) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{pile.name}</h1>
          <p className="text-sm text-slate-500">{pile.domain}</p>
        </div>
        <div className="flex items-center gap-3">
          <RunStatusBadge runId={runId} onSettled={() => {}} />
          <button
            type="button"
            onClick={handleRunPipeline}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            <FiPlay /> Run Pipeline
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-2 text-sm font-medium ${
              activeTab === tab
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'Documents' && <DocumentsTab pileId={pileId} />}
      {activeTab === 'Facts' && <FactsTab pileId={pileId} />}
      {activeTab === 'Conflicts' && <ConflictsTab pileId={pileId} />}
      {activeTab === 'Findings' && <FindingsTab pileId={pileId} />}
      {activeTab === 'Deliverable' && <DeliverableTab pileId={pileId} />}
      {activeTab === 'Rules' && <RulesTab pileId={pileId} />}
    </div>
  )
}

function DocumentsTab({ pileId }) {
  const [documents, setDocuments] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    get(`/piles/${pileId}/documents`)
      .then(setDocuments)
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="flex flex-col gap-4">
      <DocumentUpload pileId={pileId} onUploaded={refresh} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {documents === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-slate-500">No documents uploaded yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Filename</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="px-4 py-2 font-medium text-slate-900">{doc.original_filename}</td>
                  <td className="px-4 py-2 capitalize text-slate-600">{doc.doc_type}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-2 text-slate-500">{new Date(doc.ingested_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FactsTab({ pileId }) {
  const [facts, setFacts] = useState(null)
  const [documentsById, setDocumentsById] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([get(`/piles/${pileId}/facts`), get(`/piles/${pileId}/documents`)])
      .then(([factList, documents]) => {
        setFacts(factList)
        setDocumentsById(Object.fromEntries(documents.map((doc) => [doc.id, doc])))
      })
      .catch((err) => setError(err.message))
  }, [pileId])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (facts === null) return <p className="text-sm text-slate-500">Loading…</p>
  return <FactTable facts={facts} documentsById={documentsById} />
}

function ConflictsTab({ pileId }) {
  const [conflicts, setConflicts] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    get(`/piles/${pileId}/conflicts`)
      .then(setConflicts)
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (conflicts === null) return <p className="text-sm text-slate-500">Loading…</p>
  if (conflicts.length === 0) return <p className="text-sm text-slate-500">No conflicts detected.</p>

  return (
    <div className="flex flex-col gap-3">
      {conflicts.map((conflict) => (
        <ConflictCard key={conflict.id} conflict={conflict} onDecided={refresh} />
      ))}
    </div>
  )
}

function FindingsTab({ pileId }) {
  const [findings, setFindings] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    get(`/piles/${pileId}/findings`)
      .then(setFindings)
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (findings === null) return <p className="text-sm text-slate-500">Loading…</p>
  if (findings.length === 0) return <p className="text-sm text-slate-500">No findings yet.</p>

  return (
    <div className="flex flex-col gap-3">
      {findings.map((finding) => (
        <FindingCard key={finding.id} finding={finding} onDecided={refresh} />
      ))}
    </div>
  )
}

function DeliverableTab({ pileId }) {
  const [latest, setLatest] = useState(null)
  const [latestMissing, setLatestMissing] = useState(false)
  const [history, setHistory] = useState(null)
  const [draft, setDraft] = useState(null)
  const [expandedVersion, setExpandedVersion] = useState(null)
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
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function handleGenerateDraft() {
    setBusy(true)
    setError(null)
    try {
      const result = await post(`/piles/${pileId}/generate-deliverable`)
      setDraft(result)
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
        {latestMissing && <p className="text-sm text-slate-500">No deliverable has been committed yet.</p>}
        {latest && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-slate-500">Version {latest.version}</p>
            {latest.content?.sections?.map((section) => (
              <div key={section.title} className="rounded-md border border-slate-100 p-3">
                <p className="font-medium text-slate-900">{section.title}</p>
                <p className="mt-1 text-sm text-slate-600">{section.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {draft && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Pending draft (run {draft.run_id})</h2>
            <button
              type="button"
              onClick={handleCommit}
              disabled={busy}
              className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Commit Draft
            </button>
          </div>
          <p className="mb-2 text-xs text-slate-500">
            Included facts: {draft.included_fact_ids?.length ?? 0} · Excluded: {draft.excluded_fact_ids?.length ?? 0}
          </p>
          <DiffViewer diff={draft.diff} />
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
                  onClick={() =>
                    setExpandedVersion(expandedVersion === version.id ? null : version.id)
                  }
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

function RulesTab({ pileId }) {
  const [rules, setRules] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    get(`/piles/${pileId}/rules`)
      .then(setRules)
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="flex flex-col gap-4">
      <RuleForm pileId={pileId} onCreated={refresh} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {rules === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : rules.length === 0 ? (
        <p className="text-sm text-slate-500">No rules defined yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {rules.map((rule) => (
            <div key={rule.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="font-medium text-slate-900">{rule.rule_key}</p>
              <p className="text-sm text-slate-600">{rule.description}</p>
              {rule.rule_spec && (
                <pre className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-500">
                  {JSON.stringify(rule.rule_spec, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
