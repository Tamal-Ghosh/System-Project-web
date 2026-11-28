export interface SegmentationResult {
  status: 'ok'; method: 'nnunetv2' | 'segformer' | 'sam2' | 'grounded_sam2' | 'segformer_b2'; model_version: string; input_hash: string
  width: number; height: number; mask_png: string; area_pixels: number; area_fraction: number
  bounding_box: { x: number; y: number; width: number; height: number } | null
  code_revision?: string; checkpoint_sha256?: string; training_domain?: string; input_domain_supported?: boolean; threshold_source?: string
  detector?: Record<string, unknown>; detected_box?: number[]; proposal_source?: string
  prompt_box?: number[]; image_type?: 'clinical' | 'dermoscopic'; anatomical_site?: string; anatomical_conditioning?: boolean
  outside_prompt_pixels?: number; clinical_validation_status?: string; source_revision?: string
  notice?: string; threshold?: number; preprocessing_status?: string
  touches_border: boolean; elapsed_ms: number; review_required: boolean; limitations: string[]
}
export interface SegmentationAbstention { status: 'no_target' | 'ambiguous'; reason: string; input_hash: string; width: number; height: number }
export interface SegmentationStatus { status: 'ready' | 'configured' | 'unavailable'; reason: string; notice?: string; method?: string; requires_prompt?: boolean; clinical_validation_status?: string }
export async function segmentationStatus(signal: AbortSignal): Promise<SegmentationStatus> {
  const response = await fetch('/api/v1/segmentation/status', { signal })
  if (!response.ok) throw new Error('Segmentation status could not be checked.')
  return response.json()
}
export async function segmentLesion(image: Blob, signal: AbortSignal, prompt: { imageType?: 'clinical' | 'dermoscopic'; site: string }): Promise<SegmentationResult | SegmentationAbstention> {
  const body = new FormData(); body.append('image', image, 'lesion.png')
  if (prompt.imageType) body.append('image_type', prompt.imageType); body.append('site', prompt.site)
  const response = await fetch('/api/v1/segmentation', { method: 'POST', body, signal })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Segmentation failed.')
  if (['no_target', 'ambiguous'].includes(data.status) && typeof data.reason === 'string' && data.input_hash && data.width > 0 && data.height > 0) return data
  if (data.status !== 'ok' || !data.mask_png || !data.input_hash) throw new Error('Invalid segmentation response.')
  return data
}
