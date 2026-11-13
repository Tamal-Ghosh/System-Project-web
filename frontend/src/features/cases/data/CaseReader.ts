import type { CaseSummary } from '../../../contracts'

// Read-only contract: consumers do not depend on unimplemented write methods.
// Missing IDs return null; operational failures reject the promise.
export interface CaseReader {
  list(): Promise<CaseSummary[]>
  findById(id: string): Promise<CaseSummary | null>
}
