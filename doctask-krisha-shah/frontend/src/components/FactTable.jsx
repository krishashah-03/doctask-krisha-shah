import { FiAlertTriangle } from 'react-icons/fi'

export default function FactTable({ facts, documentsById, factsById, conflictedFactIds }) {
  if (facts.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No facts extracted yet — run the pipeline (or the Extract step) to pull facts out of the uploaded
        documents.
      </p>
    )
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
          {facts.map((fact) => {
            const newerFact = fact.superseded_by ? factsById?.[fact.superseded_by] : null
            const inConflict = conflictedFactIds?.has(fact.id)
            return (
              <tr key={fact.id} className={fact.superseded_by ? 'opacity-60' : undefined}>
                <td className="px-4 py-2 font-medium text-slate-900">
                  <div className="flex items-center gap-1.5">
                    {fact.fact_key}
                    {inConflict && (
                      <span title="This fact disagrees with another one — see the Conflicts tab.">
                        <FiAlertTriangle className="text-amber-500" size={13} />
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2 text-slate-700">{fact.fact_value}</td>
                <td className="px-4 py-2 text-slate-500">
                  {documentsById?.[fact.document_id]?.original_filename ?? fact.document_id}
                </td>
                <td className="px-4 py-2 text-slate-500">
                  {fact.confidence != null ? Number(fact.confidence).toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2">
                  {fact.superseded_by ? (
                    <span
                      className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                      title={
                        newerFact
                          ? `Superseded by "${newerFact.fact_value}" from ${documentsById?.[newerFact.document_id]?.original_filename ?? 'a later document'}`
                          : 'Superseded by a newer fact'
                      }
                    >
                      superseded{newerFact ? ` → ${newerFact.fact_value}` : ''}
                    </span>
                  ) : (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">current</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
