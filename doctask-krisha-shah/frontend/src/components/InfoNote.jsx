import { FiInfo } from 'react-icons/fi'

// A short, always-visible explanation of what a tab's data means — the
// whole point being that a first-time reviewer never has to guess what a
// "fact", "rule", or "finding" is or why a count is 0.
export default function InfoNote({ children }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/60 px-3 py-2.5 text-sm text-slate-600">
      <FiInfo className="mt-0.5 shrink-0 text-blue-500" />
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  )
}
