import { createContext, useContext } from 'react'
import type { ReactNode } from 'react'
import type { CaseReader } from './CaseReader'

const CaseReaderContext = createContext<CaseReader | null>(null)

export function CaseReaderProvider({ reader, children }: { reader: CaseReader; children: ReactNode }) {
  return <CaseReaderContext.Provider value={reader}>{children}</CaseReaderContext.Provider>
}

export function useCaseReader(): CaseReader {
  const reader = useContext(CaseReaderContext)
  if (!reader) throw new Error('CaseReaderProvider is required.')
  return reader
}
