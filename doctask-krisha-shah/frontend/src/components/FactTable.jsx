export default function FactTable({ facts, documentsById }) {
  if (facts.length === 0) {
    return <p className="text-sm text-slate-500">No facts extracted yet.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2">Key</th>
            <th className="px-4 py-2">Value</th>
            <th className="px-4 py-2">Document</th>
            <th className="px-4 py-2">Confidence</th>
            <th className="px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {facts.map((fact) => (
            <tr key={fact.id} className={fact.superseded_by ? 'opacity-50' : undefined}>
              <td className="px-4 py-2 font-medium text-slate-900">{fact.fact_key}</td>
              <td className="px-4 py-2 text-slate-700">{fact.fact_value}</td>
              <td className="px-4 py-2 text-slate-500">
                {documentsById?.[fact.document_id]?.original_filename ?? fact.document_id}
              </td>
              <td className="px-4 py-2 text-slate-500">
                {fact.confidence != null ? fact.confidence.toFixed(2) : '—'}
              </td>
              <td className="px-4 py-2">
                {fact.superseded_by ? (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">superseded</span>
                ) : (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">current</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
