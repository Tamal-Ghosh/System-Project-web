import { useState } from 'react'
import { Sparkles, Loader2, AlertCircle, Info, TrendingUp, TrendingDown } from 'lucide-react'
import { fetchSHAP } from '../api'
import type { AnalysisResult, SHAPResult } from '../types'

interface Props {
  result: AnalysisResult
}

export function SHAPSection({ result }: Props) {
  const [shap, setShap] = useState<SHAPResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [opacity, setOpacity] = useState(0.75)

  const handleRequest = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSHAP(result.analysis_id)
      setShap(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Failed to compute SHAP attributions')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-900">SHAP Feature Attribution (Shapley Values)</h3>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200">
              XAI
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Axiomatic game-theoretic attribution quantifying pixel-level contributions toward the diagnosis.
          </p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {!shap && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleRequest}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Calculating Shapley Values...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  View SHAP Explanation
                </>
              )}
            </button>
            <span className="text-xs text-slate-400">
              Computes Path-Integrated Shapley attributions across 12 interpolation steps.
            </span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">SHAP Computation Error</p>
              <p>{error}</p>
            </div>
          </div>
        )}

        {shap && (
          <div className="space-y-4">
            {/* Positive vs Negative Attribution Bar */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1 font-semibold text-rose-600">
                  <TrendingUp className="w-3.5 h-3.5" /> Positive Support: {shap.positive_attr_pct}%
                </span>
                <span className="flex items-center gap-1 font-semibold text-sky-600">
                  <TrendingDown className="w-3.5 h-3.5" /> Counter-Evidence: {shap.negative_attr_pct}%
                </span>
              </div>
              <div className="h-2.5 w-full bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  className="bg-rose-500 h-full transition-all duration-500"
                  style={{ width: `${shap.positive_attr_pct}%` }}
                  title={`Positive attributions: ${shap.positive_attr_pct}%`}
                />
                <div
                  className="bg-sky-500 h-full transition-all duration-500"
                  style={{ width: `${shap.negative_attr_pct}%` }}
                  title={`Negative attributions: ${shap.negative_attr_pct}%`}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>🔴 Warm/Red: Features driving towards {shap.target_class}</span>
                <span>🔵 Cool/Blue: Features opposing {shap.target_class}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Original Image */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">Original / Crop</span>
                <div className="aspect-square rounded-xl bg-slate-100 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img src={shap.original_image_url} alt="Original Lesion" className="object-contain w-full h-full" />
                </div>
              </div>

              {/* SHAP Overlay */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-slate-500">SHAP Attribution Overlay</span>
                <div className="relative aspect-square rounded-xl bg-slate-900 overflow-hidden border border-slate-200 flex items-center justify-center">
                  <img
                    src={shap.overlay_image_url}
                    alt="SHAP Attribution Overlay"
                    className="object-contain w-full h-full transition-opacity duration-200"
                    style={{ opacity }}
                  />
                </div>
              </div>
            </div>

            {/* Opacity Control */}
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-xs text-slate-600 font-medium">Attribution Overlay Opacity:</span>
              <input
                type="range"
                min="0.1"
                max="1"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-600 cursor-pointer"
              />
              <span className="text-xs font-mono text-slate-500 w-10 text-right">{(opacity * 100).toFixed(0)}%</span>
            </div>

            <div className="flex items-start gap-1.5 text-xs text-slate-400">
              <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
              <span>
                SHAP allocates credit to each input pixel based on Shapley efficiency, symmetry, and monotonicity axioms.
                Unlike Grad-CAM which looks at high-level convolutional layers, SHAP captures fine-grained input sensitivities.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
