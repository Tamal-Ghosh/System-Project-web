import type { ClassificationResult } from './classification'

export type AllergyStatus = 'none_known' | 'present' | 'unknown'

export interface MedicationEntry {
  name: string
  rxcui: string | null
  strength: string
  formulation: string
  route: string
  morning: string
  noon: string
  night: string
  duration: string
  instructions: string
}

export interface MedicineSuggestion { name: string; rxcui: string }

export interface PrescriptionFormData {
  symptoms: string[]
  allergyStatus: AllergyStatus
  allergyDetails: string
  medications: MedicationEntry[]
  followUp: string
}

export interface PrescriptionContext {
  patientId: string
  result: ClassificationResult
  assessmentId?: string | null
}

export interface Prescription {
  id: string
  assessment_id: string | null
  patient_id: string
  analysis_id: string
  model_version: string
  leading_class: string
  patient_metadata: { age: number; sex: string; site: string }
  symptoms: string[]
  allergy_status: AllergyStatus
  allergy_details: string | null
  medications: MedicationEntry[]
  follow_up: string | null
  prescriber_user_id: string | null
  prescriber_name: string | null
  created_at: string
}

async function readError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null)
  return typeof body?.detail === 'string' ? body.detail : fallback
}

export async function savePrescription(context: PrescriptionContext, form: PrescriptionFormData, signal: AbortSignal): Promise<Prescription> {
  const response = await fetch('/api/v1/prescriptions', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
    body: JSON.stringify({
      assessment_id: context.assessmentId || null,
      patient_id: context.patientId,
      analysis_id: context.result.analysis_id,
      model_version: context.result.model_version,
      leading_class: context.result.leading_class,
      patient_metadata: context.result.metadata,
      symptoms: form.symptoms, allergy_status: form.allergyStatus,
      allergy_details: form.allergyDetails || null, medications: form.medications,
      follow_up: form.followUp || null,
    }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Prescription could not be saved.'))
  return response.json()
}

export async function getPrescriptions(signal: AbortSignal): Promise<Prescription[]> {
  const response = await fetch('/api/v1/prescriptions?limit=200', { signal })
  if (!response.ok) throw new Error(await readError(response, 'Prescriptions could not be loaded.'))
  const data = await response.json()
  if (!Array.isArray(data)) throw new Error('Invalid prescriptions response.')
  return data as Prescription[]
}

export async function suggestMedicines(query: string, signal: AbortSignal): Promise<MedicineSuggestion[]> {
  const response = await fetch(`/api/v1/medicines/suggest?q=${encodeURIComponent(query)}`, { signal })
  if (!response.ok) throw new Error(await readError(response, 'Medicine suggestions are unavailable.'))
  const data = await response.json()
  return Array.isArray(data) ? data as MedicineSuggestion[] : []
}
