import { CheckCircle2, AlertTriangle, Info } from 'lucide-react'
import type { ReliabilityInfo } from '../types'

interface Props {
  info: ReliabilityInfo
}

function Row({ label, tooltip, children }: { label: string; tooltip?: string; children: React.ReactNode }) {
  return (
    <div className="py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs font-semibold text-slate-700 uppercase tracking-wide">{label}</span>
        {tooltip && (
          <span className="group relative inline-block">
            <Info className="w-3.5 h-3.5 text-slate-400 cursor-pointer" />
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block w-56 p-2 bg-slate-800 text-white text-[11px] rounded-lg shadow-lg z-50 leading-relaxed pointer-events-none">
              {tooltip}
            </span>
          </span>
        )}
      </div>
      <div className="text-sm text-slate-600">{children}</div>
    </div>
  )
}

export function ReliabilityCard({ info }: Props) {
  const levelColor =
    info.reliability_level === 'High'
      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
      : info.reliability_level === 'Moderate'
      ? 'bg-amber-50 border-amber-200 text-amber-800'
      : 'bg-rose-50 border-rose-200 text-rose-800'

  const levelBadge =
    info.reliability_level === 'High'
      ? 'bg-emerald-600'
      : info.reliability_level === 'Moderate'
      ? 'bg-amber-500'
      : 'bg-rose-600'

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">Reliability &amp; Limitations</h3>
          <p className="text-xs text-slate-400 mt-0.5">Quantified uncertainty and transparency metrics from PyTorch backend.</p>
        </div>
        {info.reliability_level && (
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full text-white ${levelBadge}`}>
            {info.reliability_level} Reliability
          </span>
        )}
      </div>

      {/* Clinical Reliability Summary Banner */}
      {info.reliability_level && (
        <div className={`mx-5 mt-4 p-3 rounded-xl border text-xs leading-relaxed ${levelColor}`}>
          <span className="font-semibold block mb-0.5">Decision-Support Reliability Assessment:</span>
          {info.uncertainty_interpretation}
        </div>
      )}

      <div className="px-5">
        {/* 1. Predictability & Confidence */}
        <Row
          label="Model Confidence & Predictability"
          tooltip="Top class probability from the ResNet50 softmax layer. A high probability reflects model internal score, not absolute certainty."
        >
          <div className="space-y-0.5">
            <span className="font-semibold text-slate-900">{(info.model_confidence * 100).toFixed(1)}%</span>
            {info.margin_to_runner_up !== undefined && (
              <span className="text-xs text-slate-500 ml-2">
                (Margin over 2nd class: <strong>+{(info.margin_to_runner_up * 100).toFixed(1)}%</strong>)
              </span>
            )}
          </div>
        </Row>

        {/* 2. Uncertainty Quantification */}
        <Row
          label="Epistemic Uncertainty Estimate"
          tooltip="Computed using Monte Carlo Dropout across stochastic forward passes. Evaluates network disagreement on lesion features."
        >
          <div className="space-y-0.5">
            <p>
              <span className="font-semibold text-slate-900">{(info.uncertainty_value * 100).toFixed(1)}%</span>
              <span className="text-slate-400 text-xs ml-2">({info.uncertainty_method})</span>
            </p>
            {info.predictability_entropy !== undefined && (
              <p className="text-xs text-slate-500">
                Predictive Entropy: <strong>{info.predictability_entropy}</strong> (0 = certain, 1 = maximum ambiguity)
              </p>
            )}
          </div>
        </Row>

        {/* 3. Calibration */}
        <Row
          label="Calibration (ECE)"
          tooltip="Expected Calibration Error (ECE) measures how closely predicted probabilities mirror actual accuracy."
        >
          <div className="space-y-0.5">
            <p className="capitalize">
              <span className="font-medium text-teal-700">{info.calibration_status.replace(/-/g, ' ')}</span>
              <span className="text-slate-400 text-xs ml-2">(ECE: {info.calibration_ece.toFixed(3)})</span>
            </p>
            <p className="text-xs text-slate-400">{info.calibration_context}</p>
          </div>
        </Row>

        {/* 4. Image quality */}
        <Row label="Image Quality Check">
          <div className="flex items-center gap-2">
            {info.image_quality_passed ? (
              <CheckCircle2 className="w-4 h-4 text-teal-500" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            )}
            <span>
              {info.image_quality_passed ? 'Quality Check Passed' : 'Potential Artifacts'} — Score:{' '}
              {(info.image_quality_score * 100).toFixed(0)}%
            </span>
          </div>
          {info.image_quality_warnings.length > 0 && (
            <ul className="text-xs text-amber-600 mt-1 space-y-0.5">
              {info.image_quality_warnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          )}
        </Row>

        {/* 5. OOD */}
        <Row
          label="Out-of-Distribution (OOD)"
          tooltip="Checks whether image features diverge from the training distribution."
        >
          <div className="flex items-center gap-1.5 text-teal-700">
            <CheckCircle2 className="w-4 h-4" />
            <span>Within expected distribution (OOD score: {info.ood_score.toFixed(3)})</span>
          </div>
        </Row>
      </div>
    </div>
  )
}
