import { Flag } from 'lucide-react'
import type { AnalysisResult } from '../types'

interface Props {
  result: AnalysisResult
}

export function PredictionCard({ result }: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-900">Model Prediction</h3>
          {result.annotated && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-teal-50 border border-teal-200 text-teal-700 text-xs font-medium rounded-full">
              Annotated ROI
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${
              result.segmentation_requested
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-slate-50 border-slate-200 text-slate-500'
            }`}
          >
            {result.segmentation_requested ? 'Segmentation: Active' : 'Segmentation: Skipped'}
          </span>
        </div>
        <span className="text-xs text-slate-400 font-mono">ID: {result.analysis_id}</span>
      </div>

      <div className="p-5 space-y-5">
        {/* Top Prediction */}
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wide">Top Classification</span>
              {result.probabilities[0]?.risk_level && (
                <span
                  className="px-2 py-0.5 text-[11px] font-semibold rounded-full text-white"
                  style={{ backgroundColor: result.probabilities[0].risk_color || '#0d9488' }}
                >
                  {result.probabilities[0].risk_level}
                </span>
              )}
            </div>
            <p className="text-2xl font-bold text-slate-900 leading-tight">{result.predicted_class_display}</p>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{result.predicted_class}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Confidence</p>
            <p className="text-2xl font-bold text-teal-600">
              {(result.probabilities[0]?.probability * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Probability Bars */}
        <div className="space-y-2.5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">All 7 HAM10000 Probabilities</p>
          {result.probabilities.map((cls, i) => {
            const isTop = i === 0
            const pct = (cls.probability * 100).toFixed(1)
            return (
              <div key={cls.label} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className={`flex items-center gap-1.5 ${isTop ? 'font-semibold text-slate-900' : 'text-slate-600'}`}>
                    {cls.code && (
                      <span className="font-mono text-[10px] uppercase px-1 py-0.2 bg-slate-100 rounded text-slate-500">
                        {cls.code}
                      </span>
                    )}
                    {cls.display_name}
                  </span>
                  <span className={isTop ? 'font-semibold text-teal-700' : 'text-slate-400'}>
                    {pct}%
                  </span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isTop ? 'bg-teal-500' : 'bg-slate-300'
                    }`}
                    style={{ width: `${Math.max(cls.probability * 100, 0.5)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Model Metadata */}
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100">
          <div><span className="font-medium text-slate-600">Architecture:</span> {result.model_name}</div>
          <div><span className="font-medium text-slate-600">Checkpoint:</span> best_model.pth (Epoch 36)</div>
          <div className="col-span-2"><span className="font-medium text-slate-600">Balanced Acc:</span> 71.3% (Focal Loss + TTA)</div>
        </div>

        {/* Clinical Recommendation Action */}
        {result.clinical_action && (
          <div className="p-3 bg-teal-50/70 border border-teal-200 rounded-xl text-xs">
            <span className="font-semibold text-teal-900 block mb-0.5">Clinical Protocol Guidance:</span>
            <p className="text-teal-800 leading-relaxed">{result.clinical_action}</p>
          </div>
        )}

        {/* Disclaimer */}
        <div className="flex items-start gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <Flag className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-slate-500 leading-relaxed">
            <strong className="text-slate-700">AI-generated research-support output.</strong> Not a confirmed diagnosis.
            Requires clinician review before any clinical decision.
          </p>
        </div>
      </div>
    </div>
  )
}
