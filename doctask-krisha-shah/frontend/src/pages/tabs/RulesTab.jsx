import { useCallback, useEffect, useState } from 'react'
import { FiChevronDown, FiChevronRight } from 'react-icons/fi'
import { get } from '../../api/client'
import RuleForm from '../../components/RuleForm'
import StatusBadge from '../../components/StatusBadge'
import InfoNote from '../../components/InfoNote'

const SEVERITY_DOT = { high: 'bg-red-500', medium: 'bg-amber-500', low: 'bg-slate-400' }

function RuleRow({ rule, findings, expanded, onToggle }) {
  const bySeverity = { high: 0, medium: 0, low: 0 }
  for (const finding of findings) {
    if (finding.severity && bySeverity[finding.severity] !== undefined) bySeverity[finding.severity] += 1
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          {findings.length > 0 ? <FiChevronDown className="text-slate-400" /> : <FiChevronRight className="text-slate-300" />}
          <div>
            <p className="font-medium text-slate-900">{rule.rule_key}</p>
            <p className="text-sm text-slate-500">{rule.description}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-xs">
          {findings.length === 0 ? (
            <span className="rounded-full bg-green-100 px-2 py-0.5 font-medium text-green-700">
              no findings
            </span>
          ) : (
            Object.entries(bySeverity)
              .filter(([, count]) => count > 0)
              .map(([severity, count]) => (
                <span key={severity} className="flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[severity]}`} />
                  {count} {severity}
                </span>
              ))
          )}
        </div>
      </button>
      {rule.rule_spec && (
        <div className="border-t border-slate-100 px-4 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Checked against</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {Object.entries(rule.rule_spec).map(([key, value]) => (
              <span key={key} className="rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-600">
                <span className="font-medium text-slate-800">{key}</span> = {String(value)}
              </span>
            ))}
          </div>
        </div>
      )}
      {expanded && findings.length > 0 && (
        <ul className="border-t border-slate-100 px-4 py-2">
          {findings.map((finding) => (
            <li key={finding.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
              <span className="text-slate-700">{finding.description}</span>
              <StatusBadge status={finding.status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function RulesTab({ pileId, refreshKey, onMutate }) {
  const [rules, setRules] = useState(null)
  const [findings, setFindings] = useState([])
  const [expandedRuleId, setExpandedRuleId] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    Promise.all([get(`/piles/${pileId}/rules`), get(`/piles/${pileId}/findings`)])
      .then(([ruleList, findingList]) => {
        setRules(ruleList)
        setFindings(findingList)
      })
      .catch((err) => setError(err.message))
  }, [pileId])

  useEffect(() => {
    refresh()
  }, [refresh, refreshKey])

  const findingsByRule = {}
  for (const finding of findings) {
    if (!finding.rule_id) continue
    ;(findingsByRule[finding.rule_id] ??= []).push(finding)
  }

  return (
    <div className="flex flex-col gap-4">
      <InfoNote>
        <p>
          A <strong>rule</strong> is a compliance check you define once, and the pipeline re-checks it against
          every fact in the pile each run. <code className="text-xs">rule_key</code> is just a label; the{' '}
          <strong>rule spec</strong> is the actual constraint (e.g. <code className="text-xs">max_days: 30</code>{' '}
          flags any extracted day-count fact above 30). Every rule violation becomes a{' '}
          <strong>finding</strong> in the Findings tab, linked back to the rule that produced it — expand a
          rule below to see its findings.
        </p>
      </InfoNote>
      <RuleForm
        pileId={pileId}
        onCreated={() => {
          refresh()
          onMutate?.()
        }}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {rules === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : rules.length === 0 ? (
        <p className="text-sm text-slate-500">
          No rules defined yet — add one above (e.g. a max payment term) to have the pipeline check every fact
          against it on the next run.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {rules.map((rule) => (
            <RuleRow
              key={rule.id}
              rule={rule}
              findings={findingsByRule[rule.id] ?? []}
              expanded={expandedRuleId === rule.id}
              onToggle={() => setExpandedRuleId(expandedRuleId === rule.id ? null : rule.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
