import { useCallback, useEffect, useState } from 'react'
import { useCaseReader } from '../data/CaseReaderProvider'

type Resource<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

function useResource<T>(load: () => Promise<T>) {
  const [resource, setResource] = useState<Resource<T>>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  // Track the loader identity so a route/provider change cannot briefly display old data.
  const [resolvedLoader, setResolvedLoader] = useState<(() => Promise<T>) | null>(null)
  useEffect(() => {
    let active = true
    setResource({ status: 'loading' })
    setResolvedLoader(() => load)
    void load().then(data => {
      if (active) setResource({ status: 'ready', data })
    }).catch(() => {
      if (active) setResource({ status: 'error', message: 'Case data could not load. Please try again.' })
    })
    return () => { active = false }
  }, [load, attempt])
  const retry = useCallback(() => setAttempt(value => value + 1), [])
  const current: Resource<T> = resolvedLoader === load ? resource : { status: 'loading' }
  return { resource: current, retry }
}

export function useCases() {
  const reader = useCaseReader()
  const load = useCallback(() => reader.list(), [reader])
  return useResource(load)
}

export function useCase(id: string) {
  const reader = useCaseReader()
  const load = useCallback(() => reader.findById(id), [reader, id])
  return useResource(load)
}
