import { useEffect, useRef, useState } from 'react'

// Polls `fetcher` every `intervalMs` while `active` is true, stopping as
// soon as `isDone(result)` returns true.
export function usePolling(fetcher, { active, intervalMs = 2000, isDone }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    if (!active) return undefined

    let cancelled = false
    let timer = null

    async function tick() {
      try {
        const result = await fetcherRef.current()
        if (cancelled) return
        setData(result)
        setError(null)
        if (!isDone(result)) {
          timer = setTimeout(tick, intervalMs)
        }
      } catch (err) {
        if (!cancelled) setError(err)
      }
    }

    tick()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [active, intervalMs])

  return { data, error }
}
