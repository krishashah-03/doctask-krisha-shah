import { Link } from 'react-router-dom'
import { FiFolder } from 'react-icons/fi'

export default function PileCard({ pile }) {
  return (
    <Link
      to={`/piles/${pile.id}`}
      className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow"
    >
      <div className="flex items-center gap-2">
        <FiFolder className="text-slate-400" />
        <span className="font-medium text-slate-900">{pile.name}</span>
      </div>
      <p className="text-sm text-slate-500">{pile.domain}</p>
      <p className="text-xs text-slate-400">Created {new Date(pile.created_at).toLocaleString()}</p>
    </Link>
  )
}
