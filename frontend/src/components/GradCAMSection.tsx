import { useState } from 'react'
import { Layers, Loader2, AlertCircle, Info } from 'lucide-react'
import { fetchGradCAM } from '../api'
import type { AnalysisResult, GradCAMResult } from '../types'

interface Props {
  result: AnalysisResult
}

export function GradCAMSection({ result }: Props) {
  const [gradcam, setGradcam] = useState<GradCAMResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [opacity, setOpacity] = useState(0.7)

  const handleRequest = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGradCAM(result.analysis_id)
      setGradcam(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Failed to generate Grad-CAM')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">Why did the model make this prediction?</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Grad-CAM visualizes the convolutional features in layer4 that influenced the ResNet50 prediction.
          </p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {!gradcam && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleRequest}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Generating Heatmap...
                </>
              ) : (
                <>
                  <Layers className="w-3.5 h-3.5" />
                  View Grad-CAM Explanation
                </>
              )}
            </button>
            <span className="text-xs text-slate-400">Generated directly from PyTorch layer4 gradients.</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Grad-CAM Error</p>
              <p>{error}</p>
            </div>
          </div>
        )}

        {gradcam && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Original Image */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">Original / Crop</span>
                <div className="aspect-square rounded-xl bg-slate-100 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img src={gradcam.original_image_url} alt="Original Lesion" className="object-contain w-full h-full" />
                </div>
              </div>

              {/* Grad-CAM Overlay */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">Grad-CAM Heatmap Overlay</span>
                <div className="relative aspect-square rounded-xl bg-slate-900 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img
                    src={gradcam.overlay_image_url}
                    alt="Grad-CAM Overlay"
                    className="object-contain w-full h-full transition-opacity duration-200"
                    style={{ opacity }}
                  />
                </div>
              </div>
            </div>

            {/* Opacity Control */}
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-xs text-slate-600 font-medium">Heatmap Intensity:</span>
              <input
                type="range"
                min="0.1"
                max="1"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(parseFloat(e.target.value))}
                className="flex-1 accent-teal-600 cursor-pointer"
              />
              <span className="text-xs font-mono text-slate-500 w-10 text-right">{(opacity * 100).toFixed(0)}%</span>
            </div>

            <div className="flex items-start gap-1.5 text-xs text-slate-400">
              <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
              <span>
                Grad-CAM highlights regions that influenced the model's output. It is an explainability tool, not proof
                of a clinical finding.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
