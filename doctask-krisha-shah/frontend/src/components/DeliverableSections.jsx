// Shared renderer for a deliverable's drafted sections, used for both the
// pending draft and the latest committed version so they look identical.
// Every citation resolves back to the fact (and document) it traces to —
// the whole point of the brief this app implements: no claim without a
// visible source.
export default function DeliverableSections({ sections, factsById = {}, documentsById = {} }) {
  if (!sections || sections.length === 0) {
    return <p className="text-sm text-slate-500">No sections in this draft.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {sections.map((section) => (
        <div key={section.title} className="rounded-md border border-slate-100 p-3">
          <p className="font-medium text-slate-900">{section.title}</p>
          <p className="mt-1 text-sm text-slate-600">{section.content}</p>
          {section.citations?.length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs font-medium text-blue-600">
                {section.citations.length} source citation{section.citations.length === 1 ? '' : 's'}
              </summary>
              <ul className="mt-1.5 flex flex-col gap-1 border-l-2 border-slate-100 pl-3">
                {section.citations.map((citation, index) => {
                  const fact = factsById[citation.fact_id]
                  const doc = fact ? documentsById[fact.document_id] : null
                  return (
                    <li key={index} className="text-xs text-slate-500">
                      "{citation.sentence}" —{' '}
                      <span className="font-medium text-slate-700">
                        {fact ? `${fact.fact_key}: ${fact.fact_value}` : citation.fact_id}
                      </span>
                      {doc && <span className="text-slate-400"> ({doc.original_filename})</span>}
                    </li>
                  )
                })}
              </ul>
            </details>
          )}
        </div>
      ))}
    </div>
  )
}
