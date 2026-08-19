import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiPlus } from 'react-icons/fi'
import { get, post } from '../api/client'
import PileCard from '../components/PileCard'

export default function PilesList() {
  const [piles, setPiles] = useState(null)
  const [error, setError] = useState(null)
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    get('/piles')
      .then(setPiles)
      .catch((err) => setError(err.message))
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setCreating(true)
    setError(null)
    try {
      const pile = await post('/piles', { name, domain })
      navigate(`/piles/${pile.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-500">Name</label>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-500">Domain</label>
          <input
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            required
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={creating}
          className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          <FiPlus /> Create Pile
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {piles === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : piles.length === 0 ? (
        <p className="text-sm text-slate-500">No piles yet — create one above.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {piles.map((pile) => (
            <PileCard key={pile.id} pile={pile} />
          ))}
        </div>
      )}
    </div>
  )
}
