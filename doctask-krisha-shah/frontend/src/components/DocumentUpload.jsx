import { useState } from 'react'
import { FiUpload } from 'react-icons/fi'
import { postForm } from '../api/client'

const DOC_TYPES = ['contract', 'amendment', 'invoice', 'other']

export default function DocumentUpload({ pileId, onUploaded }) {
  const [file, setFile] = useState(null)
  const [docType, setDocType] = useState('contract')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('doc_type', docType)
      const document = await postForm(`/piles/${pileId}/documents`, formData)
      onUploaded?.(document)
      setFile(null)
      event.target.reset()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <input
        type="file"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        className="text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-slate-200"
      />
      <select
        value={docType}
        onChange={(event) => setDocType(event.target.value)}
        className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      >
        {DOC_TYPES.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>
      <button
        type="submit"
        disabled={!file || uploading}
        className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        <FiUpload /> {uploading ? 'Uploading…' : 'Upload'}
      </button>
      {error && <p className="w-full text-sm text-red-600">{error}</p>}
    </form>
  )
}
