export const TERMINAL_STATUSES = new Set(['completed', 'failed'])

// Mirrors the stage names build_graph.py's _set_run_stage actually writes
// (extract -> extract_complete -> detect_conflicts -> ... -> completed),
// collapsed to the 4 pipeline stages a reviewer cares about.
export const PIPELINE_STEPS = [
  { key: 'extract', label: 'Extract facts' },
  { key: 'detect_conflicts', label: 'Detect conflicts' },
  { key: 'generate_deliverable', label: 'Draft deliverable' },
  { key: 'examine_rules', label: 'Examine rules' },
]

export function stepIndexFor(stage) {
  if (!stage) return -1
  if (stage.startsWith('extract')) return 0
  if (stage.startsWith('detect_conflicts')) return 1
  if (stage.startsWith('generate_deliverable')) return 2
  if (stage.startsWith('examine_rules') || stage === 'completed') return 3
  return -1
}

export function lastRunStorageKey(pileId) {
  return `doctask:lastRun:${pileId}`
}
