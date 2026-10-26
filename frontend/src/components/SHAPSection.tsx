/**
 * SHAPSection.tsx
 * ──────────────────────────────────────────────────────────────────────────────
 * Full implementation of Steps 4–8 of the SHAP XAI pipeline:
 *
 *  Step 4 – Configure Partition SHAP (budget + masking selector)
 *  Step 5 – Calculate SHAP values for the predicted class
 *  Step 6 – Display SHAP heatmap with positive / negative attribution
 *  Step 7 – Multi-class SHAP: explain all 7 HAM10000 classes
 *  Step 8 – Reliability assessment: budget comparison, masking comparison,
 *            Spearman consistency score, perturbation test
 * ──────────────────────────────────────────────────────────────────────────────
 */

import { useState } from 'react'
import {
  Sparkles, Loader2, AlertCircle, Info, TrendingUp, TrendingDown,
  ChevronDown, ChevronUp, BarChart2, ShieldCheck, Layers, RefreshCw,
} from 'lucide-react'
import {
  fetchSHAP,
  fetchSHAPAllClasses,
  fetchSHAPReliability,
} from '../api'
import type {
  AnalysisResult,
  SHAPResult,
  SHAPAllClassesResult,
  SHAPReliabilityResult,
  SHAPClassItem,
} from '../types'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Props {
  result: AnalysisResult
}

type Budget   = 'fast' | 'medium' | 'thorough'
type Masking  = 'blur' | 'inpaint' | 'constant'
type ActiveTab = 'single' | 'all-classes' | 'reliability'

// ─── Colour helpers ───────────────────────────────────────────────────────────
const riskColor = (prob: number) =>
  prob >= 0.5 ? 'text-rose-600' : prob >= 0.2 ? 'text-amber-600' : 'text-slate-500'

const consistencyColor = (rho: number) =>
  rho >= 0.80 ? 'text-emerald-600' : rho >= 0.60 ? 'text-amber-600' : 'text-rose-600'

const consistencyLabel = (rho: number) =>
  rho >= 0.80 ? 'High' : rho >= 0.60 ? 'Moderate' : 'Low'

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Attribution bar: positive (warm) + negative (cool) */
function AttrBar({ pos, neg }: { pos: number; neg: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 font-semibold text-rose-600">
          <TrendingUp className="w-3.5 h-3.5" /> Positive: {pos}%
        </span>
        <span className="flex items-center gap-1 font-semibold text-sky-600">
          <TrendingDown className="w-3.5 h-3.5" /> Counter: {neg}%
        </span>
      </div>
      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden flex">
        <div
          className="bg-rose-500 h-full transition-all duration-500"
          style={{ width: `${pos}%` }}
        />
        <div
          className="bg-sky-500 h-full transition-all duration-500"
          style={{ width: `${neg}%` }}
        />
      </div>
    </div>
  )
}

/** Single class explanation card for Step 7 grid */
function ClassCard({ item, baseUrl }: { item: SHAPClassItem; baseUrl: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 transition text-xs font-medium text-slate-700"
      >
        <span className="flex items-center gap-2">
          <span className={`font-bold ${riskColor(item.pred_prob)}`}>
            {(item.pred_prob * 100).toFixed(1)}%
          </span>
          <span className="truncate">{item.class_display}</span>
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5 flex-shrink-0" /> : <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />}
      </button>
      {open && (
        <div className="p-3 space-y-2">
          <div className="aspect-square rounded-lg overflow-hidden bg-slate-900 border border-slate-200">
            <img
              src={`${baseUrl}${item.overlay_image_url}`}
              alt={`SHAP for ${item.class_display}`}
              className="w-full h-full object-contain"
            />
          </div>
          <AttrBar pos={item.positive_attr_pct} neg={item.negative_attr_pct} />
          <p className="text-[10px] text-slate-400">Elapsed: {item.elapsed_s}s</p>
        </div>
      )}
    </div>
  )
}

// ─── Main Component ────────────────────────────────────────────────────────────
export function SHAPSection({ result }: Props) {
  // ── State ──────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ActiveTab>('single')

  // Step 4 – configuration
  const [budget,  setBudget]  = useState<Budget>('fast')
  const [masking, setMasking] = useState<Masking>('blur')
  const [targetClassIdx, setTargetClassIdx] = useState<number>(
    result.probabilities.findIndex(p => p.label === result.predicted_class) >= 0
      ? result.probabilities.findIndex(p => p.label === result.predicted_class)
      : 0
  )
  const [opacity, setOpacity] = useState(0.75)

  // Step 5–6 – single-class result
  const [shap,       setShap]       = useState<SHAPResult | null>(null)
  const [loadingSingle, setLoadingSingle] = useState(false)
  const [errorSingle,   setErrorSingle]   = useState<string | null>(null)

  // Step 7 – all-classes result
  const [shapAll,   setShapAll]   = useState<SHAPAllClassesResult | null>(null)
  const [loadingAll, setLoadingAll] = useState(false)
  const [errorAll,   setErrorAll]   = useState<string | null>(null)

  // Step 8 – reliability result
  const [reliability, setReliability] = useState<SHAPReliabilityResult | null>(null)
  const [loadingRel,  setLoadingRel]  = useState(false)
  const [errorRel,    setErrorRel]    = useState<string | null>(null)

  // Backend base URL (empty string → same origin via Vite proxy)
  const baseUrl = ''

  // ── Handlers ───────────────────────────────────────────────────────────────

  /** Step 5–6: compute SHAP for selected class */
  const handleSingle = async () => {
    setLoadingSingle(true)
    setErrorSingle(null)
    try {
      const data = await fetchSHAP(result.analysis_id, {
        budget,
        masking,
        targetClassIdx,
      })
      setShap(data)
    } catch (e: any) {
      setErrorSingle(e.response?.data?.detail || e.message || 'SHAP computation failed')
    } finally {
      setLoadingSingle(false)
    }
  }

  /** Step 7: compute SHAP for all 7 classes */
  const handleAllClasses = async () => {
    setLoadingAll(true)
    setErrorAll(null)
    try {
      const data = await fetchSHAPAllClasses(result.analysis_id, 'fast', masking === 'inpaint' ? 'blur' : masking)
      setShapAll(data)
    } catch (e: any) {
      setErrorAll(e.response?.data?.detail || e.message || 'Multi-class SHAP failed')
    } finally {
      setLoadingAll(false)
    }
  }

  /** Step 8: reliability assessment */
  const handleReliability = async () => {
    setLoadingRel(true)
    setErrorRel(null)
    try {
      const data = await fetchSHAPReliability(result.analysis_id, masking === 'inpaint' ? 'blur' : masking, targetClassIdx)
      setReliability(data)
    } catch (e: any) {
      setErrorRel(e.response?.data?.detail || e.message || 'Reliability assessment failed')
    } finally {
      setLoadingRel(false)
    }
  }

  // ── Tab labels ─────────────────────────────────────────────────────────────
  const tabs: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'single',       label: 'Single Class',   icon: <Sparkles className="w-3.5 h-3.5" /> },
    { id: 'all-classes',  label: 'All Classes',    icon: <Layers className="w-3.5 h-3.5" /> },
    { id: 'reliability',  label: 'Reliability',    icon: <ShieldCheck className="w-3.5 h-3.5" /> },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">

      {/* ── Header ── */}
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-slate-900">SHAP Feature Attribution</h3>
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200">
            Partition SHAP
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 bg-violet-50 text-violet-700 rounded-full border border-violet-200">
            ImageMasker
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Real SHAP library (v0.54+) · Steps 4–8 · Blur masking · Partition explainer
        </p>
      </div>

      {/* ── Step 4: Configuration panel ── */}
      <div className="px-5 pt-4 pb-3 border-b border-slate-100 bg-slate-50">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Step 4 — Configure Explainer
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">

          {/* Budget selector */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600 flex items-center gap-1">
              <BarChart2 className="w-3 h-3" /> Evaluation Budget
            </label>
            <select
              value={budget}
              onChange={e => setBudget(e.target.value as Budget)}
              className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="fast">Fast (50 evals) — ~10-15 s ✓</option>
              <option value="medium">Medium (100 evals) — ~20-35 s</option>
              <option value="thorough">Thorough (200 evals) — ~45-90 s</option>
            </select>
          </div>

          {/* Masking strategy */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600 flex items-center gap-1">
              <Layers className="w-3 h-3" /> Masking Strategy
            </label>
            <select
              value={masking}
              onChange={e => setMasking(e.target.value as Masking)}
              className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="blur">Gaussian Blur (21×21) ✓</option>
              <option value="inpaint">Inpaint (Telea)</option>
              <option value="constant">Constant Zero (Black)</option>
            </select>
          </div>

          {/* Target class selector */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Target Class
            </label>
            <select
              value={targetClassIdx}
              onChange={e => { setTargetClassIdx(Number(e.target.value)); setShap(null) }}
              className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {result.probabilities.map((p, i) => (
                <option key={p.label} value={i}>
                  [{(p.probability * 100).toFixed(1)}%] {p.display_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Masking note */}
        <div className="flex items-start gap-1.5 mt-3 text-[11px] text-slate-400">
          <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>
            Masking strategy determines how SHAP hides image regions. Gaussian blur keeps textures
            realistic; constant-zero creates artificial black patches. Different strategies
            can produce different attribution maps.
          </span>
        </div>
      </div>

      {/* ── Tab switcher ── */}
      <div className="flex border-b border-slate-100">
        {tabs.map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition border-b-2 ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-700 bg-indigo-50'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="p-5 space-y-4">

        {/* ══════════════════════════════════════════════════════════════════
            Tab 1 – Steps 5 & 6: Single Class SHAP
        ══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'single' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSingle}
                disabled={loadingSingle}
                className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {loadingSingle
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Computing…</>
                  : <><Sparkles className="w-3.5 h-3.5" /> Compute SHAP (Step 5)</>}
              </button>
              {shap && (
                <button
                  type="button"
                  onClick={() => { setShap(null) }}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Reset
                </button>
              )}
              <span className="text-xs text-slate-400">
                {budget === 'fast' ? '~50' : budget === 'medium' ? '~100' : '~200'} masked evaluations · {masking} masker
              </span>
            </div>

            {errorSingle && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">SHAP Computation Error</p>
                  <p>{errorSingle}</p>
                </div>
              </div>
            )}

            {shap && (
              <div className="space-y-4">

                {/* Step 6 – Metadata banner */}
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-xs space-y-1">
                  <div className="flex flex-wrap gap-3">
                    <span className="text-slate-600">
                      <span className="font-medium">Explained class:</span>{' '}
                      <span className="font-bold text-indigo-700">{shap.target_class}</span>
                    </span>
                    <span className="text-slate-600">
                      <span className="font-medium">Predicted probability:</span>{' '}
                      <span className="font-bold">{(shap.pred_prob * 100).toFixed(1)}%</span>
                    </span>
                    <span className="text-slate-600">
                      <span className="font-medium">Method:</span>{' '}
                      <span className="font-mono text-slate-500">{shap.explanation_method}</span>
                    </span>
                    <span className="text-slate-600">
                      <span className="font-medium">Elapsed:</span>{' '}
                      {shap.elapsed_s}s
                    </span>
                  </div>
                  {!shap.shap_available && (
                    <p className="text-amber-700 flex items-center gap-1 mt-1">
                      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                      Partition SHAP unavailable — Integrated Gradients approximation used.
                    </p>
                  )}
                </div>

                {/* Step 6 – Attribution bar */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <AttrBar pos={shap.positive_attr_pct} neg={shap.negative_attr_pct} />
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>🔴 Warm / Red: pixels supporting <em>{shap.target_class}</em></span>
                    <span>🔵 Cool / Blue: pixels opposing <em>{shap.target_class}</em></span>
                  </div>
                </div>

                {/* Step 6 – Image comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-slate-500">Original / Crop</span>
                    <div className="aspect-square rounded-xl bg-slate-100 overflow-hidden border border-slate-200 flex items-center justify-center">
                      <img
                        src={`${baseUrl}${shap.original_image_url}`}
                        alt="Original Lesion"
                        className="object-contain w-full h-full"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-slate-500">SHAP Attribution Overlay</span>
                    <div className="relative aspect-square rounded-xl bg-slate-900 overflow-hidden border border-slate-200 flex items-center justify-center">
                      <img
                        src={`${baseUrl}${shap.overlay_image_url}`}
                        alt="SHAP Attribution Overlay"
                        className="object-contain w-full h-full transition-opacity duration-200"
                        style={{ opacity }}
                      />
                    </div>
                  </div>
                </div>

                {/* Opacity slider */}
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-xs text-slate-600 font-medium">Overlay Opacity:</span>
                  <input
                    type="range" min="0.1" max="1" step="0.05"
                    value={opacity}
                    onChange={e => setOpacity(parseFloat(e.target.value))}
                    className="flex-1 accent-indigo-600 cursor-pointer"
                  />
                  <span className="text-xs font-mono text-slate-500 w-10 text-right">
                    {(opacity * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Step 6 – Interpretation guide */}
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 space-y-1">
                  <p className="font-semibold">How to Interpret (Step 6)</p>
                  <ul className="list-disc list-inside space-y-0.5 text-amber-700">
                    <li><strong>Warm/red regions</strong> increase the probability of <em>{shap.target_class}</em> relative to the blur baseline.</li>
                    <li><strong>Cool/blue regions</strong> decrease that probability — they favour other classes.</li>
                    <li>A highlighted region does not prove clinical correctness; SHAP explains the model's behaviour, not its accuracy.</li>
                    <li>Low evaluation budgets may produce coarse or unstable attributions.</li>
                  </ul>
                </div>

                <div className="flex items-start gap-1.5 text-xs text-slate-400">
                  <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                  <span>
                    Partition SHAP evaluates ~{budget === 'fast' ? 50 : budget === 'medium' ? 100 : 200} masked variants on a 56×56 image (upsampled to 224×224). Timeout: 5 min.
                    The masking strategy is <strong>{masking}</strong>. Axiomatic properties: efficiency, symmetry, monotonicity.
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            Tab 2 – Step 7: All Classes
        ══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'all-classes' && (
          <div className="space-y-4">
            <div className="p-3 bg-violet-50 border border-violet-200 rounded-xl text-xs text-violet-800">
              <p className="font-semibold mb-1">Step 7 — Class-Specific SHAP Explanations</p>
              <p>
                Generate attribution maps for all 7 HAM10000 classes using the same image.
                Uses the <strong>fast</strong> budget (50 evals/class) to keep it tractable.
                Compare which regions drive each class's predicted probability.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleAllClasses}
                disabled={loadingAll}
                className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {loadingAll
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Running 7 explanations…</>
                  : <><Layers className="w-3.5 h-3.5" /> Explain All 7 Classes</>}
              </button>
              <span className="text-xs text-slate-400">~7 × 50 evaluations · {masking} masker</span>
            </div>

            {errorAll && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div><p className="font-semibold">Error</p><p>{errorAll}</p></div>
              </div>
            )}

            {shapAll && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Expand any class to view its SHAP heatmap.</span>
                  <span className="font-mono">{shapAll.budget} budget · {shapAll.masking} mask</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                  {shapAll.classes
                    .slice()
                    .sort((a, b) => b.pred_prob - a.pred_prob)
                    .map(item => (
                      <ClassCard key={item.class_idx} item={item} baseUrl={baseUrl} />
                    ))}
                </div>

                {/* Cross-class note */}
                <div className="flex items-start gap-1.5 text-xs text-slate-400">
                  <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span>
                    Each attribution map is computed independently for its target class.
                    Do not assume the predicted-class explanation generalises to other classes.
                    Keep the image, preprocessing, and masking settings consistent when comparing.
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            Tab 3 – Step 8: Reliability Assessment
        ══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'reliability' && (
          <div className="space-y-4">
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
              <p className="font-semibold mb-1">Step 8 — Reliability & Stability Assessment</p>
              <ul className="list-disc list-inside space-y-0.5 text-emerald-700">
                <li>Budget comparison: fast / medium / thorough attribution maps side-by-side.</li>
                <li>Masking comparison: blur vs. constant-zero (black) masker.</li>
                <li>Spearman ρ consistency score between fast and medium maps.</li>
                <li>Perturbation test: ΔP when top-50% positive pixels are blurred.</li>
              </ul>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleReliability}
                disabled={loadingRel}
                className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {loadingRel
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Assessing reliability…</>
                  : <><ShieldCheck className="w-3.5 h-3.5" /> Run Reliability Assessment</>}
              </button>
              <span className="text-xs text-slate-400">
                Runs 5 SHAP explanations (fast + medium + thorough + 2 maskers)
              </span>
            </div>

            {errorRel && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div><p className="font-semibold">Error</p><p>{errorRel}</p></div>
              </div>
            )}

            {reliability && (
              <div className="space-y-5">

                {/* Consistency + Perturbation summary */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Spearman ρ</p>
                    <p className={`text-2xl font-bold ${consistencyColor(reliability.consistency_score)}`}>
                      {reliability.consistency_score.toFixed(3)}
                    </p>
                    <p className={`text-xs font-medium mt-0.5 ${consistencyColor(reliability.consistency_score)}`}>
                      {consistencyLabel(reliability.consistency_score)} Consistency
                    </p>
                    <p className="text-[10px] text-slate-400 mt-1">fast vs medium maps</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Perturbation ΔP</p>
                    <p className={`text-2xl font-bold ${reliability.perturbation_delta >= 0.05 ? 'text-emerald-600' : reliability.perturbation_delta >= 0 ? 'text-amber-600' : 'text-rose-600'}`}>
                      {reliability.perturbation_delta >= 0 ? '+' : ''}{reliability.perturbation_delta.toFixed(3)}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {(reliability.orig_prob * 100).toFixed(1)}% → {(reliability.perturbed_prob * 100).toFixed(1)}%
                    </p>
                    <p className="text-[10px] text-slate-400 mt-1">after blurring top-50% positive pixels</p>
                  </div>
                </div>

                {/* Interpretation text */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 space-y-1">
                  <p className="font-semibold">Interpretation</p>
                  <p>{reliability.interpretation}</p>
                </div>

                {/* Budget comparison */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                    <BarChart2 className="w-3.5 h-3.5" /> Budget Comparison
                  </p>
                  <div className="grid grid-cols-3 gap-3">
                    {reliability.budget_comparison.map(b => (
                      <div key={b.budget} className="space-y-1.5">
                        <div className="aspect-square rounded-lg overflow-hidden bg-slate-900 border border-slate-200">
                          <img
                            src={`${baseUrl}${b.overlay_url}`}
                            alt={`Budget ${b.budget}`}
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <div className="text-[10px] text-slate-500 space-y-0.5 px-0.5">
                          <p className="font-semibold capitalize">{b.budget}</p>
                          <p>Prob: {(b.pred_prob * 100).toFixed(1)}%</p>
                          <p>+{b.positive_attr_pct}% / −{b.negative_attr_pct}%</p>
                          <p className="text-slate-400">{b.elapsed_s}s</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Masking comparison */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5" /> Masking Strategy Comparison
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    {reliability.masking_comparison.map(m => (
                      <div key={m.masking} className="space-y-1.5">
                        <div className="aspect-square rounded-lg overflow-hidden bg-slate-900 border border-slate-200">
                          <img
                            src={`${baseUrl}${m.overlay_url}`}
                            alt={`Masking ${m.masking}`}
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <div className="text-[10px] text-slate-500 space-y-0.5 px-0.5">
                          <p className="font-semibold capitalize">{m.masking}</p>
                          <p>+{m.positive_attr_pct}% / −{m.negative_attr_pct}%</p>
                          <p className="text-slate-400">{m.elapsed_s}s</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Step 8 limitations note */}
                <div className="flex items-start gap-1.5 text-xs text-slate-400">
                  <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Important limitation (Step 8):</strong> Removing or blurring image regions
                    creates images that may differ substantially from genuine skin lesion photographs.
                    Perturbation results must be interpreted with caution. A visually appealing heatmap
                    is not necessarily a faithful explanation. Consistency across budgets supports
                    but does not guarantee reliability.
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
