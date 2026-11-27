import type { ClassificationResult } from './classification'

export type AssessmentDecision = 'agree' | 'disagree' | 'unsure'
export type NextAction = 'routine_follow_up' | 'dermatology_referral' | 'biopsy_consideration' | 'additional_assessment' | 'other'

export interface AssessmentFormData {
  patientId: string
  patientName: string
  imageSnapshot: string | null
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
  patient_name: string | null
  analysis_id: string
  model_version: string
  leading_class: string
  model_scores: { label: string; score: number }[]
  patient_metadata: { age: number; sex: string; site: string }
  image_snapshot: string | null
  uncertainty: { normalized_entropy: number; top_two_margin: number }
  ensemble: { member_count: number; agreement: number | null }
  input_policy: string
  tta: boolean
  limitations: string[]
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
      patient_name: form.patientName,
      analysis_id: result.analysis_id,
      model_version: result.model_version,
      leading_class: result.leading_class,
      model_scores: result.scores,
      patient_metadata: result.metadata,
      image_snapshot: form.imageSnapshot,
      uncertainty: result.uncertainty,
      ensemble: result.ensemble,
      input_policy: result.input_policy,
      tta: result.tta,
      limitations: result.limitations,
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
  const response = await fetch('/api/v1/assessments?limit=5', { signal })
  if (!response.ok) throw new Error(await readError(response, 'Reports could not be loaded.'))
  const data = await response.json()
  if (!Array.isArray(data)) throw new Error('Invalid reports response.')
  return data as DoctorAssessment[]
}

export async function updateAssessment(
  id: string,
  form: Pick<AssessmentFormData, 'decision' | 'confidence' | 'suspectedDiagnosis' | 'differentialDiagnoses' | 'clinicalNote' | 'nextAction'>,
  signal: AbortSignal
): Promise<DoctorAssessment> {
  const response = await fetch(`/api/v1/assessments/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      decision: form.decision,
      confidence: form.confidence,
      suspected_diagnosis: form.suspectedDiagnosis || null,
      differential_diagnoses: form.differentialDiagnoses,
      clinical_note: form.clinicalNote || null,
      next_action: form.nextAction,
    }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Report could not be updated.'))
  return response.json()
}

export async function deleteAssessment(id: string, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`/api/v1/assessments/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    signal,
  })
  if (!response.ok) throw new Error(await readError(response, 'Report could not be deleted.'))
}
