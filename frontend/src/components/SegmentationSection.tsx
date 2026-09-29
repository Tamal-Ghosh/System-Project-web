import { useState } from 'react'
import { Scissors, Loader2, AlertCircle, Info } from 'lucide-react'
import { fetchSegmentation } from '../api'
import type { AnalysisResult, SegmentationResult } from '../types'

interface Props {
  result: AnalysisResult
}

export function SegmentationSection({ result }: Props) {
  const [seg, setSeg] = useState<SegmentationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [opacity, setOpacity] = useState(0.8)

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSegmentation(result.analysis_id)
      setSeg(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Segmentation failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">Lesion Boundary Segmentation (Optional)</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Generates lesion contour boundary, area, perimeter, and asymmetry metrics.
          </p>
        </div>
        <span className="text-xs text-slate-500 font-medium px-2 py-0.5 bg-slate-100 rounded-full">
          {result.segmentation_requested ? 'Requested Upfront' : 'Optional Action'}
        </span>
      </div>

      <div className="p-5 space-y-4">
        {!seg && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
            <div>
              <p className="text-xs font-semibold text-slate-800">
                {result.segmentation_requested
                  ? 'Boundary segmentation ready to render.'
                  : 'Segmentation was not enabled during initial upload.'}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Click to compute the exact boundary mask and geometric metrics.
              </p>
            </div>
            <button
              type="button"
              onClick={handleRun}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-medium rounded-xl transition flex-shrink-0 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Segmenting...
                </>
              ) : (
                <>
                  <Scissors className="w-3.5 h-3.5" />
                  Run Segmentation
                </>
              )}
            </button>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Segmentation Error</p>
              <p>{error}</p>
            </div>
          </div>
        )}

        {seg && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Mask */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">Binary Mask</span>
                <div className="aspect-square rounded-xl bg-slate-950 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img src={seg.mask_url} alt="Segmentation Mask" className="object-contain w-full h-full" />
                </div>
              </div>

              {/* Contour Overlay */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">Contour Boundary Overlay</span>
                <div className="relative aspect-square rounded-xl bg-slate-900 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img
                    src={seg.overlay_url}
                    alt="Segmentation Overlay"
                    className="object-contain w-full h-full"
                    style={{ opacity }}
                  />
                </div>
              </div>
            </div>

            {/* Opacity Control */}
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-xs text-slate-600 font-medium">Overlay Opacity:</span>
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

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                <p className="text-[11px] text-slate-400 uppercase tracking-wide">Area</p>
                <p className="text-base font-bold text-slate-900 mt-0.5">{seg.metrics.area_px.toLocaleString()} px</p>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                <p className="text-[11px] text-slate-400 uppercase tracking-wide">Perimeter</p>
                <p className="text-base font-bold text-slate-900 mt-0.5">{seg.metrics.perimeter_px} px</p>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                <p className="text-[11px] text-slate-400 uppercase tracking-wide">Circularity</p>
                <p className="text-base font-bold text-teal-700 mt-0.5">{seg.metrics.circularity.toFixed(3)}</p>
              </div>
            </div>

            <div className="flex items-start gap-1.5 text-xs text-slate-400">
              <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
              <span>
                Segmentation output is model-generated and requires clinician review before clinical use.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
