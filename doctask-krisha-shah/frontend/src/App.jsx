import { NavLink, Route, Routes } from 'react-router-dom'
import { FiInbox, FiLayers } from 'react-icons/fi'
import PilesList from './pages/PilesList'
import PileDetail from './pages/PileDetail'
import PendingReview from './pages/PendingReview'

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
  }`

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <span className="text-lg font-semibold text-slate-900">Document Pile Review</span>
          <nav className="flex gap-2">
            <NavLink to="/" end className={navLinkClass}>
              <FiLayers /> Piles
            </NavLink>
            <NavLink to="/review" className={navLinkClass}>
              <FiInbox /> Pending Review
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<PilesList />} />
          <Route path="/piles/:pileId" element={<PileDetail />} />
          <Route path="/review" element={<PendingReview />} />
        </Routes>
      </main>
    </div>
  )
}
