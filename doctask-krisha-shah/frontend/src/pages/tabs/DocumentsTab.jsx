import { useCallback, useEffect, useState } from 'react'
import { get } from '../../api/client'
import DocumentUpload from '../../components/DocumentUpload'
import StatusBadge from '../../components/StatusBadge'
import InfoNote from '../../components/InfoNote'

export default function DocumentsTab({ pileId, onMutate }) {
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
      <InfoNote>
        <p>
          Upload the documents that make up this pile — contracts, amendments, invoices, anything in the
          mixed formats you're comparing. Once uploaded, click <strong>Run Pipeline</strong> above to extract
          facts, detect conflicts, and draft the deliverable.
        </p>
      </InfoNote>
      <DocumentUpload
        pileId={pileId}
        onUploaded={() => {
          refresh()
          onMutate?.()
        }}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {documents === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-slate-500">No documents uploaded yet — add one above to get started.</p>
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
