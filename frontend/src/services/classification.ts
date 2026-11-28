export interface ClassificationResult {
  analysis_id: string; model_version: string; leading_class: string
  scores: { label: string; score: number }[]
  uncertainty: { normalized_entropy: number; top_two_margin: number }
  ensemble: { member_count: number; agreement: number | null }
  metadata: { age: number; sex: string; site: string }
  input_policy: string; tta: boolean; elapsed_ms: number; limitations: string[]
  input_hash: string
  assistant_access_token?: string | null
  decision_scores?: Record<string, number>
  positive_categories?: string[]
  calibration?: { applied: boolean; temperature: number | null; reason: string; artifact_id?: string }
  uncalibrated_scores?: { label: string; score: number }[] | null
  decision_scores_basis?: string
}

export interface ExplanationResponse {
  status: 'ok' | 'unavailable'; reason?: string; method?: 'integrated_gradients'; score?: 'fold_logit'
  target_class?: string; target_class_index?: number; fold?: number; fold_selection?: string; model_version?: string; tta?: 'none'
  input_hash?: string; baseline?: 'blur' | 'zero'; n_steps?: number; convergence_delta?: number
  image_map?: { encoding: 'png_base64'; width: number; height: number; crop: { x: number; y: number; w: number; h: number }; resize_factor: number; data: string; signed: number[][]; abs: number[][] }
  metadata_attribution?: { base_value: number; full_value: number; features: Record<'age' | 'sex' | 'site', number>; note: string }
  elapsed_ms?: number; limitations?: string
}
export interface ExplanationRequest {
  image: Blob; age: number; sex: string; site: string; targetClass?: string; fold?: number
  baseline: 'blur' | 'zero'; nSteps: number; includeMetadata: boolean; signal: AbortSignal
}
export async function classify(image: Blob, age: number, sex: string, site: string, signal: AbortSignal, clinical?: Blob): Promise<ClassificationResult> {
  const body = new FormData()
  if (clinical) body.append('clinical', clinical, 'clinical.png')
  body.append('image', image, 'lesion.png'); body.append('age', String(age)); body.append('sex', sex); body.append('site', site)
  const response = await fetch('/api/v1/analyses', { method: 'POST', body, signal })
  const raw = await response.text()
  let data: any = null
  try { data = JSON.parse(raw) } catch { /* Include plain-text proxy errors in the message. */ }
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : typeof data?.message === 'string' ? data.message : raw.trim()
    throw new Error(detail ? `Classification request failed (${response.status}): ${detail.slice(0, 240)}` : `Classification request failed (${response.status}).`)
  }
  if (!data || !Array.isArray(data.scores) || data.scores.length !== 11 || !data.uncertainty) throw new Error('Invalid model response.')
  return data as ClassificationResult
}

export async function requestExplanation(
  request: ExplanationRequest,
  onStageChange?: (stage: string) => void
): Promise<ExplanationResponse> {
  const body = new FormData()
  body.append('image', request.image, 'lesion.png'); body.append('age', String(request.age))
  body.append('sex', request.sex); body.append('site', request.site)
  body.append('method', 'integrated_gradients'); body.append('n_steps', String(request.nSteps))
  body.append('baseline', request.baseline); body.append('include_metadata', String(request.includeMetadata))
  if (request.targetClass) body.append('target_class', request.targetClass)
  if (request.fold != null) body.append('fold', String(request.fold))

  const response = await fetch('/api/v1/explanations', { method: 'POST', body, signal: request.signal })
  const raw = await response.text()
  let data: any = null
  try { data = JSON.parse(raw) } catch { /* Include plain-text proxy errors */ }
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : typeof data?.message === 'string' ? data.message : raw.trim()
    throw new Error(detail ? `Explanation request failed (${response.status}): ${detail.slice(0, 240)}` : `Explanation request failed (${response.status}).`)
  }

  // Handle immediate cached completion or synchronous fallback
  if (data?.result) return data.result as ExplanationResponse
  if (data?.status === 'ok') return data as ExplanationResponse

  const jobId = data?.job_id
  if (!jobId) {
    throw new Error('Invalid explanation job initialization.')
  }

  // Poll for background job completion
  const deadline = Date.now() + 25 * 60 * 1000
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 2500))
    if (request.signal.aborted) throw new DOMException('Aborted', 'AbortError')

    const pollRes = await fetch(`/api/v1/explanations/${jobId}`, { signal: request.signal })
    if (!pollRes.ok) throw new Error(`Status check failed (${pollRes.status})`)
    const jobData = await pollRes.json()

    if (jobData.stage && onStageChange) {
      onStageChange(jobData.stage)
    }

    if (jobData.status === 'done') {
      return jobData.result as ExplanationResponse
    }
    if (jobData.status === 'failed') {
      throw new Error(jobData.error || 'Explanation generation failed.')
    }
  }
  throw new Error('Explanation request timed out.')
}
