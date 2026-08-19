const STATUS_COLORS = {
  new: 'text-green-700 bg-green-50 border-green-200',
  changed: 'text-amber-700 bg-amber-50 border-amber-200',
  unchanged: 'text-slate-500 bg-slate-50 border-slate-200',
  removed: 'text-red-700 bg-red-50 border-red-200 line-through',
}

export default function DiffViewer({ diff }) {
  if (!diff || diff.length === 0) {
    return <p className="text-sm text-slate-500">No diff available.</p>
  }
  return (
    <ul className="flex flex-col gap-1.5">
      {diff.map((entry) => (
        <li
          key={entry.title}
          className={`flex items-center justify-between rounded-md border px-3 py-1.5 text-sm ${STATUS_COLORS[entry.status] || ''}`}
        >
          <span>{entry.title}</span>
          <span className="text-xs font-medium uppercase tracking-wide">{entry.status}</span>
        </li>
      ))}
    </ul>
  )
}
