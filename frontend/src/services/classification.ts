export interface ClassificationResult {
  analysis_id: string; model_version: string; leading_class: string
  scores: { label: string; score: number }[]
  uncertainty: { normalized_entropy: number; top_two_margin: number }
  ensemble: { member_count: number; agreement: number | null }
  metadata: { age: number; sex: string; site: string }
  input_policy: string; tta: boolean; elapsed_ms: number; limitations: string[]
}
export async function classify(image: Blob, age: number, sex: string, site: string, signal: AbortSignal): Promise<ClassificationResult> {
  const body = new FormData()
  body.append('image', image, 'lesion.png'); body.append('age', String(age)); body.append('sex', sex); body.append('site', site)
  const response = await fetch('/api/v1/analyses', { method: 'POST', body, signal })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : `Classification request failed (${response.status}).`)
  if (!data || !Array.isArray(data.scores) || data.scores.length !== 11 || !data.uncertainty) throw new Error('Invalid model response.')
  return data as ClassificationResult
}
