import axios from 'axios'
import type {
  AnalysisResult,
  GradCAMResult,
  SHAPResult,
  SHAPAllClassesResult,
  SHAPReliabilityResult,
  SegmentationResult,
  ChatSource,
  LesionAnnotation,
} from './types'

const client = axios.create({
  timeout: 60000,
})

export async function runClassification(
  file: File,
  annotation?: LesionAnnotation | null,
  enableSegmentation: boolean = false,
  studyId?: string,
  onProgress?: (pct: number) => void
): Promise<AnalysisResult> {
  const formData = new FormData()
  formData.append('image', file)
  if (studyId) formData.append('study_id', studyId)
  if (enableSegmentation) formData.append('run_segmentation', 'true')

  if (annotation?.hasAnnotation && annotation.roiBbox) {
    formData.append('roi_x', String(annotation.roiBbox.x))
    formData.append('roi_y', String(annotation.roiBbox.y))
    formData.append('roi_w', String(annotation.roiBbox.width))
    formData.append('roi_h', String(annotation.roiBbox.height))
  }

  const res = await client.post<AnalysisResult>('/api/v1/analyses', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })

  return {
    ...res.data,
    annotation: annotation ?? null,
  }
}

export async function fetchGradCAM(analysisId: string): Promise<GradCAMResult> {
  const res = await client.post<GradCAMResult>(`/api/v1/analyses/${analysisId}/explanation`)
  return res.data
}

export async function fetchSHAP(
  analysisId: string,
  options?: {
    budget?: 'fast' | 'medium' | 'thorough'
    masking?: 'blur' | 'inpaint' | 'constant'
    targetClassIdx?: number
  }
): Promise<SHAPResult> {
  const params: Record<string, string | number> = {}
  if (options?.budget) params['budget'] = options.budget
  if (options?.masking) params['masking'] = options.masking
  if (options?.targetClassIdx !== undefined) params['target_class_idx'] = options.targetClassIdx
  const res = await client.post<SHAPResult>(
    `/api/v1/analyses/${analysisId}/shap`,
    null,
    { params }
  )
  return res.data
}

export async function fetchSHAPAllClasses(
  analysisId: string,
  budget: 'fast' | 'medium' = 'fast',
  masking: 'blur' | 'constant' = 'blur'
): Promise<SHAPAllClassesResult> {
  const res = await client.post<SHAPAllClassesResult>(
    `/api/v1/analyses/${analysisId}/shap/all-classes`,
    null,
    { params: { budget, masking } }
  )
  return res.data
}

export async function fetchSHAPReliability(
  analysisId: string,
  masking: 'blur' | 'constant' = 'blur',
  targetClassIdx?: number
): Promise<SHAPReliabilityResult> {
  const params: Record<string, string | number> = { masking }
  if (targetClassIdx !== undefined) params['target_class_idx'] = targetClassIdx
  const res = await client.post<SHAPReliabilityResult>(
    `/api/v1/analyses/${analysisId}/shap/reliability`,
    null,
    { params }
  )
  return res.data
}

export async function fetchSegmentation(analysisId: string): Promise<SegmentationResult> {
  const res = await client.post<SegmentationResult>(`/api/v1/analyses/${analysisId}/segmentation`)
  return res.data
}

export async function sendChatMessage(
  message: string,
  conversationId?: string,
  analysisId?: string
): Promise<{
  message_id: string
  content: string
  sources?: ChatSource[]
  tool_used?: string
  conversation_id: string
}> {
  const res = await client.post('/api/v1/chat', {
    message,
    conversation_id: conversationId,
    analysis_id: analysisId,
  })
  return res.data
}
