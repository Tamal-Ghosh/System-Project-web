export interface ReliabilityBin {
  lower: number
  upper: number
  count: number
  confidence: number
  accuracy: number
}

export interface CalibrationEvidence {
  status: 'measured_oof'
  artifact_id: string
  model_family: string
  model_version: string
  scope: string
  sample_count: number
  class_count: number
  metrics: { top_label_ece: number; brier_score: number }
  reliability_bins: ReliabilityBin[]
  temperature_scaling: {
    applied: boolean
    temperature: number | null
    reason: string
    fit_samples?: number
    evaluation_samples?: number
    evaluation_metrics_before?: { nll: number; top_label_ece: number; brier_score: number; accuracy: number }
    evaluation_metrics_after?: { nll: number; top_label_ece: number; brier_score: number; accuracy: number }
  }
  limitations: string[]
}

export async function getCalibrationEvidence(signal: AbortSignal): Promise<CalibrationEvidence> {
  const response = await fetch('/api/v1/model/calibration', { signal })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error('Calibration evidence is currently unavailable.')
  if (!data || data.status !== 'measured_oof' || !Array.isArray(data.reliability_bins)) {
    throw new Error('Invalid calibration evidence response.')
  }
  return data as CalibrationEvidence
}
