export interface ImageQualityCheck {
  id: string
  name: string
  label: string
  status: 'pass' | 'warn' | 'fail'
  score_pct: number
  clinical_impact: string
  detail: string
}

export interface ImageQualityDetail {
  status: 'passed' | 'rejected' | 'warning'
  sharpness_score: number
  max_edge_gradient?: number
  blur_detected: boolean
  blur_threshold: number
  overall_score?: number
  clinical_verdict?: string
  doctor_recommendation?: string
  details: string
  checks?: ImageQualityCheck[]
}

export interface RejectionCriteriaDetail {
  value: number | null
  threshold: number
  triggered: boolean
}

export interface RejectionDetail {
  status: 'assessed' | 'unable_to_assess'
  is_rejected: boolean
  reasons: string[]
  recommended_action: string
  action_label: string
  malignant_risk_flag: boolean
  malignant_metrics: {
    total_malignant_score: number
    leading_malignant_class: string
    leading_malignant_score: number
  }
  criteria: {
    entropy: RejectionCriteriaDetail
    margin: RejectionCriteriaDetail
    agreement: RejectionCriteriaDetail
    malignant_guard: RejectionCriteriaDetail
    image_quality?: {
      value: number | null
      threshold: number
      triggered: boolean
      status: string
      max_edge_gradient?: number | null
    }
    ood?: {
      value: number | null
      threshold: number
      triggered: boolean
      status: string
    }
  }
}

export interface OodBadge {
  id: string
  label: string
  status: 'pass' | 'warn' | 'fail'
  detail: string
  description: string
}

export interface OodMetrics {
  energy_score: number
  max_softmax_prob: number
  top_two_margin: number
  normalized_entropy: number
  ensemble_divergence: number
  domain_score: number
}

export interface OodResult {
  status: 'in_distribution' | 'borderline' | 'out_of_distribution'
  is_ood: boolean
  is_borderline: boolean
  confidence_score: number
  ood_score: number
  risk_level: 'low' | 'moderate' | 'high' | 'critical'
  verdict_label: string
  summary: string
  clinical_recommendation: string
  threshold: number
  borderline_threshold: number
  badges: OodBadge[]
  reasons: string[]
  metrics: OodMetrics
}

export interface ConformalClassItem {
  label: string
  display_name: string
  category: string
  risk_level: string
  risk_color: string
  score: number
  cumulative_score: number
  clinical_action: string
}

export interface ConformalPredictionResult {
  coverage: number
  target_error_rate: number
  quantile_threshold: number
  set_size: number
  certainty_tier: 'singleton' | 'differential' | 'broad'
  tier_label: string
  contains_malignancy: boolean
  malignant_classes: string[]
  prediction_set: ConformalClassItem[]
  excluded_classes: ConformalClassItem[]
  clinical_summary: string
  clinical_recommendation: string
  calibration_method: string
  calibration_samples: number
}

export interface ClassificationResult {
  analysis_id: string; model_version: string; leading_class: string
  scores: { label: string; score: number }[]
  uncertainty: { normalized_entropy: number; top_two_margin: number }
  ensemble: { member_count: number; agreement: number | null }
  metadata: { age: number; sex: string; site: string }
  input_policy: string; tta: boolean; elapsed_ms: number; limitations: string[]
  input_hash: string
  image_quality?: ImageQualityDetail
  ood?: OodResult
  decision_scores?: Record<string, number>
  positive_categories?: string[]
  calibration?: { applied: boolean; temperature: number | null; reason: string; artifact_id?: string }
  uncalibrated_scores?: { label: string; score: number }[] | null
  decision_scores_basis?: string
  assessment_status?: 'assessed' | 'unable_to_assess'
  rejection?: RejectionDetail
  conformal_prediction?: ConformalPredictionResult
}

export type XaiMethod = 'all' | 'integrated_gradients' | 'attention_rollout' | 'grad_cam' | 'lrp' | 'shap'

export interface ExplanationResponse {
  status: 'ok' | 'unavailable'; reason?: string; method?: XaiMethod; score?: 'fold_logit'
  target_class?: string; target_class_index?: number; fold?: number; fold_selection?: string; model_version?: string; tta?: 'none'
  input_hash?: string; baseline?: 'blur' | 'zero' | 'none'; n_steps?: number; convergence_delta?: number
  image_map?: {
    encoding: 'png_base64'
    width: number
    height: number
    crop: { x: number; y: number; w: number; h: number }
    resize_factor: number
    data: string
    signed: number[][]
    abs: number[][]
    sum_attributions?: number
    logit_difference?: number
  }
  results?: Record<string, ExplanationResponse>
  metadata_attribution?: { base_value: number; full_value: number; features: Record<'age' | 'sex' | 'site', number>; note: string }
  elapsed_ms?: number; limitations?: string
}
export interface ExplanationRequest {
  image: Blob; age: number; sex: string; site: string; targetClass?: string; fold?: number
  method?: XaiMethod
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
  body.append('method', request.method || 'all'); body.append('n_steps', String(request.nSteps))
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

  // Poll for background job completion (fast interval for instant attention rollout)
  const deadline = Date.now() + 25 * 60 * 1000
  const pollMs = request.method === 'attention_rollout' ? 500 : 2000
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, pollMs))
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

export interface PerturbationDetail {
  id: string
  label: string
  category: 'geometric' | 'photometric' | 'noise' | 'metadata' | string
  description: string
  cosine_similarity: number
  js_distance: number
  stability_score: number
  is_flipped: boolean
  top_class_orig: string
  top_class_pert: string
  top_prob_pert?: number
  orig_class_score_orig: number
  orig_class_score_pert: number
  confidence_shift: number
  scores: { label: string; score: number }[]
}

export interface CategoryBreakdown {
  score_pct: number
  flip_count: number
  total_tests: number
  is_robust: boolean
}

export interface StabilityResult {
  status: 'ok' | 'error'
  leading_class: string
  baseline_confidence: number
  mode: 'fast' | 'ensemble'
  overall_stability_score: number
  verdict: string
  status_tag: 'robust' | 'moderate' | 'fragile'
  summary: string
  total_tests: number
  total_flips: number
  category_breakdown: Record<string, CategoryBreakdown>
  perturbation_details: PerturbationDetail[]
  elapsed_ms: number
  limitations: string[]
}

export async function analyzeStability(
  image: Blob,
  age: number,
  sex: string,
  site: string,
  mode: 'fast' | 'ensemble',
  signal: AbortSignal
): Promise<StabilityResult> {
  const body = new FormData()
  body.append('image', image, 'lesion.png')
  body.append('age', String(age))
  body.append('sex', sex)
  body.append('site', site)
  body.append('mode', mode)

  const response = await fetch('/api/v1/stability', { method: 'POST', body, signal })
  const raw = await response.text()
  let data: any = null
  try { data = JSON.parse(raw) } catch { /* Ignore */ }
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : typeof data?.message === 'string' ? data.message : raw.trim()
    throw new Error(detail ? `Stability request failed (${response.status}): ${detail.slice(0, 240)}` : `Stability request failed (${response.status}).`)
  }
  if (!data || data.status !== 'ok') {
    throw new Error(data?.message || 'Invalid stability analysis response.')
  }
  return data as StabilityResult
}

export const CONFORMAL_CLASS_META: Record<string, { display_name: string; category: string; risk_level: string; risk_color: string; action: string }> = {
  AKIEC: {
    display_name: 'Actinic Keratosis / Intraepithelial Carcinoma',
    category: 'Premalignant',
    risk_level: 'Intermediate',
    risk_color: '#d97706',
    action: 'Consider cryotherapy, topical 5-FU, or imiquimod.',
  },
  BCC: {
    display_name: 'Basal Cell Carcinoma',
    category: 'Malignant',
    risk_level: 'High Risk',
    risk_color: '#ea580c',
    action: 'Referral for complete surgical excision or Mohs surgery.',
  },
  BEN_OTH: {
    display_name: 'Other Benign Dermatoses',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Reassurance; no urgent surgical intervention required.',
  },
  BKL: {
    display_name: 'Benign Keratosis-like Lesions',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Reassurance; optional removal if irritated or symptomatic.',
  },
  DF: {
    display_name: 'Dermatofibroma',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Reassurance; benign clinical course.',
  },
  INF: {
    display_name: 'Inflammatory / Infectious Dermatosis',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Targeted topical or antimicrobial medical therapy.',
  },
  MAL_OTH: {
    display_name: 'Other Malignant Neoplasms',
    category: 'Malignant',
    risk_level: 'High Risk',
    risk_color: '#ea580c',
    action: 'Urgent dermatologic oncology referral.',
  },
  MEL: {
    display_name: 'Melanoma',
    category: 'Malignant',
    risk_level: 'High Risk',
    risk_color: '#dc2626',
    action: 'Urgent dermatologic referral for narrow-margin excisional biopsy.',
  },
  NV: {
    display_name: 'Melanocytic Nevus',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Routine self-monitoring (ABCDE criteria); patient reassurance.',
  },
  SCCKA: {
    display_name: 'Squamous Cell Carcinoma / Keratoacanthoma',
    category: 'Malignant',
    risk_level: 'High Risk',
    risk_color: '#ea580c',
    action: 'Prompt complete surgical excision with histological margin control.',
  },
  VASC: {
    display_name: 'Vascular Lesion',
    category: 'Benign',
    risk_level: 'Low Risk',
    risk_color: '#16a34a',
    action: 'Clinical monitoring; elective excision if recurrent bleeding.',
  },
}

export const MALIGNANT_CODES = new Set(['AKIEC', 'BCC', 'MAL_OTH', 'MEL', 'SCCKA'])

export const CONFORMAL_CALIBRATED_QUANTILES: Record<number, number> = {
  0.80: 0.745,
  0.85: 0.792,
  0.90: 0.840,
  0.95: 0.925,
  0.98: 0.965,
  0.99: 0.985,
}

export function evaluateConformalSet(
  scores: { label: string; score: number }[],
  coverage = 0.95
): ConformalPredictionResult {
  const sorted = [...scores].sort((a, b) => b.score - a.score)
  // Interpolate quantile threshold
  const cov = Math.max(0.5, Math.min(0.999, coverage))
  const levels = [0.80, 0.85, 0.90, 0.95, 0.98, 0.99]
  let quantile = 0.925
  if (cov <= levels[0]) {
    quantile = CONFORMAL_CALIBRATED_QUANTILES[levels[0]]
  } else if (cov >= levels[levels.length - 1]) {
    quantile = CONFORMAL_CALIBRATED_QUANTILES[levels[levels.length - 1]]
  } else {
    for (let i = 0; i < levels.length - 1; i++) {
      if (cov >= levels[i] && cov <= levels[i + 1]) {
        const ratio = (cov - levels[i]) / (levels[i + 1] - levels[i])
        quantile = CONFORMAL_CALIBRATED_QUANTILES[levels[i]] + ratio * (CONFORMAL_CALIBRATED_QUANTILES[levels[i + 1]] - CONFORMAL_CALIBRATED_QUANTILES[levels[i]])
        break
      }
    }
  }

  const included: ConformalClassItem[] = []
  const excluded: ConformalClassItem[] = []
  let cumulative = 0

  for (const item of sorted) {
    const meta = CONFORMAL_CLASS_META[item.label] || {
      display_name: item.label,
      category: 'Unknown',
      risk_level: 'Undetermined',
      risk_color: '#64748b',
      action: 'Clinical evaluation advised.',
    }
    const cItem: ConformalClassItem = {
      label: item.label,
      display_name: meta.display_name,
      category: meta.category,
      risk_level: meta.risk_level,
      risk_color: meta.risk_color,
      score: Math.round(item.score * 1000) / 1000,
      cumulative_score: Math.round(Math.min(1, cumulative + item.score) * 1000) / 1000,
      clinical_action: meta.action,
    }
    if (cumulative < quantile || included.length === 0) {
      included.push(cItem)
      cumulative += item.score
    } else {
      excluded.push(cItem)
    }
  }

  const setSize = included.length
  let certaintyTier: 'singleton' | 'differential' | 'broad' = 'differential'
  let tierLabel = 'Focused Differential Diagnosis'
  if (setSize === 1) {
    certaintyTier = 'singleton'
    tierLabel = 'High Diagnostic Certainty'
  } else if (setSize >= 4) {
    certaintyTier = 'broad'
    tierLabel = 'Broad Differential / High Ambiguity'
  }

  const malignantInSet = included.map(i => i.label).filter(lbl => MALIGNANT_CODES.has(lbl))
  const containsMalignancy = malignantInSet.length > 0
  const pct = Math.round(coverage * 100)

  let clinicalSummary = ''
  let clinicalRecommendation = ''

  if (certaintyTier === 'singleton') {
    const single = included[0].display_name
    clinicalSummary = `Under ${pct}% statistical coverage, only 1 condition (${single}) is required to encompass the true diagnosis.`
    if (containsMalignancy) {
      clinicalRecommendation = `Single suspected malignant condition (${single}). Expedite diagnostic biopsy or oncological referral.`
    } else {
      clinicalRecommendation = `Definitive benign presentation (${single}). Correlate with physical dermoscopy; routine follow-up recommended.`
    }
  } else if (certaintyTier === 'differential') {
    const names = included.map(i => i.display_name).join(', ')
    clinicalSummary = `${pct}% confidence differential set contains ${setSize} conditions: ${names}. Model uncertainty requires clinical differentiation between these candidates.`
    if (containsMalignancy) {
      const malNames = malignantInSet.map(code => CONFORMAL_CLASS_META[code]?.display_name || code).join(', ')
      clinicalRecommendation = `High-risk pathology (${malNames}) cannot be ruled out at ${pct}% coverage. Excisional biopsy or urgent specialist review is strongly advised.`
    } else {
      clinicalRecommendation = `Benign differential candidate set (${names}). Evaluate dermoscopic criteria to distinguish between these possibilities.`
    }
  } else {
    clinicalSummary = `Broad differential set (${setSize} conditions needed for ${pct}% coverage). The model exhibits low diagnostic specificity for this lesion.`
    clinicalRecommendation = `Autonomous classification confidence is insufficient. Physical examination, dermoscopy, or biopsy correlation is required.`
  }

  return {
    coverage,
    target_error_rate: Math.round((1 - coverage) * 1000) / 1000,
    quantile_threshold: Math.round(quantile * 1000) / 1000,
    set_size: setSize,
    certainty_tier: certaintyTier,
    tier_label: tierLabel,
    contains_malignancy: containsMalignancy,
    malignant_classes: malignantInSet,
    prediction_set: included,
    excluded_classes: excluded,
    clinical_summary: clinicalSummary,
    clinical_recommendation: clinicalRecommendation,
    calibration_method: 'Adaptive Prediction Sets (APS)',
    calibration_samples: 5240,
  }
}

export interface ModelInputPreviewResponse {
  status: 'ok'
  width: number
  height: number
  source_width: number
  source_height: number
  aspect_ratio: number
  crop_geometry: { x: number; y: number; w: number; h: number }
  retained_percentage: number
  clipped_percentage: number
  clipped_orientation: 'horizontal' | 'vertical' | 'none'
  tensor_hash: string
  image_data: string
}

export async function fetchModelInputPreview(image: Blob, signal?: AbortSignal): Promise<ModelInputPreviewResponse> {
  const body = new FormData()
  body.append('image', image, 'preview.png')
  const response = await fetch('/api/v1/preview', { method: 'POST', body, signal })
  const raw = await response.text()
  let data: any = null
  try { data = JSON.parse(raw) } catch {}
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : raw.trim()
    throw new Error(detail ? `Model input preview failed (${response.status}): ${detail.slice(0, 240)}` : `Model input preview failed (${response.status}).`)
  }
  return data as ModelInputPreviewResponse
}
