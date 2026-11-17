import type { ClassificationResult } from './classification'

export type AssessmentDecision = 'agree' | 'disagree' | 'unsure'
export type NextAction = 'routine_follow_up' | 'dermatology_referral' | 'biopsy_consideration' | 'additional_assessment' | 'other'

export interface AssessmentFormData {
  patientId: string
  decision: AssessmentDecision
  confidence: number
  suspectedDiagnosis: string
  differentialDiagnoses: string[]
  clinicalNote: string
  nextAction: NextAction
}

export interface DoctorAssessment {
  id: string
  patient_id: string | null
  analysis_id: string
  model_version: string
  leading_class: string
  model_scores: { label: string; score: number }[]
  patient_metadata: { age: number; sex: string; site: string }
  decision: AssessmentDecision
  confidence: number
  suspected_diagnosis: string | null
  differential_diagnoses: string[]
  clinical_note: string | null
  next_action: NextAction
  reviewer_user_id: string | null
  reviewer_name: string | null
  created_at: string
}

async function readError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null)
  return typeof body?.detail === 'string' ? body.detail : fallback
}

export async function saveAssessment(result: ClassificationResult, form: AssessmentFormData, signal: AbortSignal): Promise<DoctorAssessment> {
  const response = await fetch('/api/v1/assessments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      patient_id: form.patientId,
      analysis_id: result.analysis_id,
      model_version: result.model_version,
      leading_class: result.leading_class,
      model_scores: result.scores,
      patient_metadata: result.metadata,
      decision: form.decision,
      confidence: form.confidence,
      suspected_diagnosis: form.suspectedDiagnosis || null,
      differential_diagnoses: form.differentialDiagnoses,
      clinical_note: form.clinicalNote || null,
      next_action: form.nextAction,
    }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Assessment could not be saved.'))
  return response.json()
}

export async function getAssessments(signal: AbortSignal): Promise<DoctorAssessment[]> {
  const response = await fetch('/api/v1/assessments?limit=100', { signal })
  if (!response.ok) throw new Error(await readError(response, 'Reviews could not be loaded.'))
  const data = await response.json()
  if (!Array.isArray(data)) throw new Error('Invalid reviews response.')
  return data as DoctorAssessment[]
}
