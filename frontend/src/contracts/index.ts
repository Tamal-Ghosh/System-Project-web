// Shared frontend contract. Keep aligned with the future FastAPI OpenAPI schema.
export type CaseStatus = 'draft' | 'awaiting_review' | 'reviewed'
export type AnalysisStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface CaseSummary {
  id: string
  patientCode: string
  bodySite: string
  updatedAt: string
  status: CaseStatus
}

export interface AnalysisResult {
  id: string
  caseId: string
  inputVersionId: string
  modelVersion: string
  preprocessingVersion: string
  status: AnalysisStatus
  classScores: { classId: string; label: string; score: number }[]
  qualityWarnings: { code: string; message: string; blocking: boolean }[]
  explanationReferences: string[]
}
