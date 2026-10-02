export interface ClassProbability {
  code?: string
  label: string
  display_name: string
  probability: number
  risk_level?: string
  risk_color?: string
}

export interface ReliabilityInfo {
  model_confidence: number
  uncertainty_value: number
  uncertainty_method: string
  uncertainty_interpretation: string
  calibration_status: string
  calibration_ece: number
  calibration_context: string
  image_quality_score: number
  image_quality_passed: boolean
  image_quality_warnings: string[]
  ood_detected: boolean
  ood_score: number
  ood_warning?: string | null
  reliability_level?: string
  predictability_entropy?: number
  margin_to_runner_up?: number
}

export interface LesionAnnotation {
  hasAnnotation: boolean
  mode: 'freehand' | 'bbox' | 'none'
  roiBbox?: { x: number; y: number; width: number; height: number }
  strokePoints?: Array<{ x: number; y: number }>
}

export interface AnalysisResult {
  analysis_id: string
  predicted_class: string
  predicted_class_display: string
  probabilities: ClassProbability[]
  model_name: string
  model_version: string
  created_at: string
  reliability: ReliabilityInfo
  warnings: string[]
  image_url: string
  annotated: boolean
  segmentation_requested: boolean
  annotation?: LesionAnnotation | null
  clinical_action?: string
}

export interface GradCAMResult {
  analysis_id: string
  original_image_url: string
  overlay_image_url: string
  target_class: string
  explanation_method: string
  generated_at: string
}

export interface SHAPResult {
  analysis_id: string
  original_image_url: string
  overlay_image_url: string
  target_class: string
  explanation_method: string
  positive_attr_pct: number
  negative_attr_pct: number
  generated_at: string
}

export interface SegmentationResult {
  analysis_id: string
  mask_url: string
  overlay_url: string
  metrics: {
    area_px: number
    perimeter_px: number
    circularity: number
  }
  generated_at: string
}

export interface ChatSource {
  id: string
  title: string
  page_or_section?: string
  url?: string
  excerpt?: string
  document_type?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  sources?: ChatSource[]
  tool_used?: string
  is_loading?: boolean
  is_error?: boolean
}
