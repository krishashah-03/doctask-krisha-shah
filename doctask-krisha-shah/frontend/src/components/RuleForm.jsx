import { useState } from 'react'
import { FiPlus, FiTrash2 } from 'react-icons/fi'
import { post } from '../api/client'

export default function RuleForm({ pileId, onCreated }) {
  const [ruleKey, setRuleKey] = useState('')
  const [description, setDescription] = useState('')
  const [specPairs, setSpecPairs] = useState([{ key: '', value: '' }])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function updatePair(index, field, value) {
    setSpecPairs((pairs) => pairs.map((pair, i) => (i === index ? { ...pair, [field]: value } : pair)))
  }

  function addPair() {
    setSpecPairs((pairs) => [...pairs, { key: '', value: '' }])
  }

  function removePair(index) {
    setSpecPairs((pairs) => pairs.filter((_, i) => i !== index))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const rule_spec = {}
      for (const { key, value } of specPairs) {
        if (!key.trim()) continue
        const numeric = Number(value)
        rule_spec[key.trim()] = value.trim() !== '' && !Number.isNaN(numeric) ? numeric : value
      }
      const rule = await post(`/piles/${pileId}/rules`, {
        rule_key: ruleKey,
        description,
        rule_spec: Object.keys(rule_spec).length > 0 ? rule_spec : null,
      })
      onCreated?.(rule)
      setRuleKey('')
      setDescription('')
      setSpecPairs([{ key: '', value: '' }])
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex gap-3">
        <input
          value={ruleKey}
          onChange={(event) => setRuleKey(event.target.value)}
          placeholder="rule_key (e.g. max_payment_term_days)"
          required
          className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
      </div>
      <textarea
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Description"
        required
        rows={2}
        className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      />
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Rule spec (key / value)</p>
        {specPairs.map((pair, index) => (
          <div key={index} className="flex gap-2">
            <input
              value={pair.key}
              onChange={(event) => updatePair(index, 'key', event.target.value)}
              placeholder="key (e.g. max_days)"
              className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
            <input
              value={pair.value}
              onChange={(event) => updatePair(index, 'value', event.target.value)}
              placeholder="value (e.g. 30)"
              className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={() => removePair(index)}
              className="rounded-md px-2 text-slate-400 hover:bg-slate-100 hover:text-red-600"
            >
              <FiTrash2 />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addPair}
          className="inline-flex w-fit items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        >
          <FiPlus /> Add field
        </button>
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="w-fit rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {submitting ? 'Creating…' : 'Create Rule'}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  )
}
