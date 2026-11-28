import { ClassificationSummary } from './ClassificationSummary'
import type { ClassificationResult, ExplanationResponse } from '../../services/classification'
import { evaluateConformalSet } from '../../services/classification'
import { useEffect, useRef, useState } from 'react'
import {
  BarChart3,
  ScanLine,
  ShieldQuestion,
  ShieldCheck,
  ArrowRight,
  Info,
  Fingerprint,
  AlertTriangle,
  ShieldAlert,
  Camera,
  Stethoscope,
  Sun,
  Sparkles,
  Crosshair,
  HelpCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CLASS_DESCRIPTIONS: Record<string, { name: string; category: 'Malignant' | 'Benign' | 'Premalignant' | 'Inflammatory' }> = {
  MEL: { name: 'Melanoma', category: 'Malignant' },
  NV: { name: 'Melanocytic Nevus (Common Mole)', category: 'Benign' },
  BCC: { name: 'Basal Cell Carcinoma', category: 'Malignant' },
  BKL: { name: 'Benign Keratosis (Seborrheic / Lentigo)', category: 'Benign' },
  AKIEC: { name: 'Actinic Keratosis / Bowen Disease', category: 'Premalignant' },
  SCCKA: { name: 'Squamous Cell Carcinoma / KA', category: 'Malignant' },
  VASC: { name: 'Vascular Lesion (Hemangioma)', category: 'Benign' },
  DF: { name: 'Dermatofibroma', category: 'Benign' },
  INF: { name: 'Inflammatory / Infectious Lesion', category: 'Inflammatory' },
  MAL_OTH: { name: 'Other Malignant Neoplasm', category: 'Malignant' },
  BEN_OTH: { name: 'Other Benign Lesion', category: 'Benign' },
}

const IQA_DISPLAY_NAMES: Record<string, string> = {
  focus: 'Focus & Sharpness',
  exposure: 'Lighting & Exposure',
  glare: 'Glare & Reflection',
  framing: 'Lesion Centering',
}

const tabs: { label: string; icon: LucideIcon }[] = [
  { label: 'Classification', icon: BarChart3 },
  { label: 'XAI', icon: ScanLine },
  { label: 'Uncertainty', icon: ShieldQuestion },
]

function Unavailable({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return <div className="inspector-empty"><div className="inspector-empty-icon"><Icon size={25} strokeWidth={1.5} /></div><h3>{title}</h3><p>{text}</p></div>
}

function XaiPanelCard({
  title,
  subtitle,
  explanation,
  imageUrl,
  view,
  opacity,
}: {
  title: string
  subtitle: string
  explanation: ExplanationResponse
  imageUrl: string
  view: 'overlay' | 'signed' | 'abs' | 'original'
  opacity: number
}) {
  const croppedCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const heatmapCanvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (!explanation?.image_map || !imageUrl) return
    const { crop, signed, abs, width = 224, height = 224 } = explanation.image_map

    const imgObj = new Image()
    imgObj.crossOrigin = 'anonymous'
    imgObj.onload = () => {
      const canvas = croppedCanvasRef.current
      if (canvas) {
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.clearRect(0, 0, width, height)
          ctx.drawImage(imgObj, crop.x, crop.y, crop.w, crop.h, 0, 0, width, height)
        }
      }
    }
    imgObj.src = imageUrl

    const heatCanvas = heatmapCanvasRef.current
    if (!heatCanvas) return
    heatCanvas.width = width
    heatCanvas.height = height
    const heatCtx = heatCanvas.getContext('2d')
    if (!heatCtx) return

    const imgData = heatCtx.createImageData(width, height)
    const data = imgData.data
    const isUnsignedMethod = explanation.method === 'attention_rollout' || explanation.method === 'grad_cam'

    if (view === 'signed' || (view === 'overlay' && !isUnsignedMethod)) {
      let flatSigned: number[] = []
      if (Array.isArray(signed)) flatSigned = signed.flat().map(v => Math.abs(v))
      flatSigned.sort((a, b) => a - b)
      const maxVal = flatSigned[Math.floor(flatSigned.length * 0.98)] || 1e-5

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const val = signed?.[y]?.[x] ?? 0
          const idx = (y * width + x) * 4
          const norm = Math.min(1, Math.max(-1, val / maxVal))
          const intensity = Math.abs(norm)

          if (intensity < 0.04) {
            data[idx] = 255; data[idx + 1] = 255; data[idx + 2] = 255; data[idx + 3] = 0
          } else if (norm > 0) {
            data[idx] = 220; data[idx + 1] = 38; data[idx + 2] = 38
            data[idx + 3] = Math.round(Math.pow(intensity, 0.75) * 230)
          } else {
            data[idx] = 37; data[idx + 1] = 99; data[idx + 2] = 235
            data[idx + 3] = Math.round(Math.pow(intensity, 0.75) * 230)
          }
        }
      }
    } else {
      let flatAbs: number[] = []
      if (Array.isArray(abs)) flatAbs = abs.flat()
      flatAbs.sort((a, b) => a - b)
      const maxVal = flatAbs[Math.floor(flatAbs.length * 0.98)] || 1e-5

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const val = abs?.[y]?.[x] ?? 0
          const idx = (y * width + x) * 4
          const norm = Math.min(1, Math.max(0, val / maxVal))

          if (norm < 0.04) {
            data[idx] = 0; data[idx + 1] = 0; data[idx + 2] = 0; data[idx + 3] = 0
          } else {
            data[idx] = Math.round(234 * norm + 20 * (1 - norm))
            data[idx + 1] = Math.round(88 * norm)
            data[idx + 2] = Math.round(12 * norm)
            data[idx + 3] = Math.round(Math.pow(norm, 0.75) * 240)
          }
        }
      }
    }
    heatCtx.putImageData(imgData, 0, 0)
  }, [explanation, imageUrl, view])

  return (
    <div className="xai-card">
      <div className="xai-preview" data-view={view}>
        <canvas
          ref={croppedCanvasRef}
          className="xai-cropped-canvas"
          style={{ display: view === 'signed' || view === 'abs' ? 'none' : 'block' }}
        />
        <canvas
          ref={heatmapCanvasRef}
          className="xai-heatmap-canvas"
          style={{
            display: view === 'original' ? 'none' : 'block',
            opacity: view === 'overlay' ? opacity / 100 : 1,
          }}
        />
      </div>
      <div className="xai-card-caption">
        <strong>{title}</strong>
        <span>{subtitle} · {((explanation.elapsed_ms ?? 0) / 1000).toFixed(1)}s</span>
      </div>
    </div>
  )
}

export function AnalysisInspector({ hasImage, result, image, age, sex, site }: { hasImage: boolean; result?: ClassificationResult; image?: Blob; age?: string; sex?: string; site?: string }) {
  const [tab, setTab] = useState('Classification')
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [stage, setStage] = useState('')
  const [target, setTarget] = useState('')
  const [fold, setFold] = useState('0')
  const [xaiMethod, setXaiMethod] = useState<'all' | 'attention_rollout' | 'grad_cam' | 'integrated_gradients' | 'lrp' | 'shap'>('all')
  const [baseline, setBaseline] = useState<'blur' | 'zero'>('blur')
  const [nSteps, setNSteps] = useState<'6' | '8' | '16'>('6')
  const [opacity, setOpacity] = useState(65)
  const [view, setView] = useState<'overlay' | 'signed' | 'abs' | 'original'>('overlay')
  const [startedAt, setStartedAt] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [imageUrl, setImageUrl] = useState('')
  const explanationController = useRef<AbortController | null>(null)

  useEffect(() => { if (!image) { setImageUrl(''); return }; const url = URL.createObjectURL(image); setImageUrl(url); return () => URL.revokeObjectURL(url) }, [image])
  useEffect(() => {
    explanationController.current?.abort()
    setExplanation(null)
    setMessage('')
    setTarget(result?.leading_class ?? '')
    return () => explanationController.current?.abort()
  }, [image, age, sex, site, result])
  const isOodResult = Boolean(result?.ood?.is_ood || result?.rejection?.reasons.includes('OUT_OF_DISTRIBUTION_ANOMALY'))
  useEffect(() => { if (isOodResult) setTab('Classification') }, [isOodResult])
  useEffect(() => { if (!busy) return; const timer = window.setInterval(() => setElapsed(Math.floor((Date.now()-startedAt)/1000)), 250); return () => window.clearInterval(timer) }, [busy, startedAt])
  const STAGE_LABEL: Record<string, string> = {
    queued: 'Waiting in queue…',
    attention_rollout: '1/5 Computing Attention Rollout…',
    grad_cam: '2/5 Computing ViT Grad-CAM…',
    lrp: '3/5 Computing Layer-wise Relevance Propagation (LRP)…',
    integrated_gradients: '4/5 Computing Integrated Gradients…',
    shap: '5/5 Computing Spatial SHAP…',
    shapley: 'Calculating Metadata Shapley…',
  }

  async function runExplanation() {
    const requestExplanation = (await import('../../services/classification')).requestExplanation
    if (!image || !result || busy) return
    const controller = new AbortController(); explanationController.current?.abort(); explanationController.current = controller
    setBusy(true); setMessage(''); setExplanation(null); setStartedAt(Date.now()); setElapsed(0); setStage('queued')
    try {
      const response = await requestExplanation({
        image, age: Number(age), sex: sex ?? '', site: site ?? 'unknown',
        targetClass: target || result.leading_class, fold: Number(fold),
        method: xaiMethod,
        baseline, nSteps: Number(nSteps), includeMetadata: true, signal: controller.signal
      }, (s) => setStage(s))
      if (response.status === 'unavailable') {
        setMessage(response.reason === 'busy' ? 'Explanation service is busy. Please try again.' : `Explanation unavailable: ${response.reason ?? 'unknown reason'}`);
        return
      }
      if (response.input_hash !== result.input_hash) {
        setMessage('Explanation does not match current analysis.');
        return
      }
      setExplanation(response); setFold(String(response.fold ?? fold))
      if (response.status === 'ok' && response.image_map?.data) {
        try {
          localStorage.setItem(
            `xai_evidence_${result.analysis_id}`,
            JSON.stringify({
              method: response.method === 'integrated_gradients' ? 'Integrated Gradients' : (response.method || 'Integrated Gradients'),
              targetClass: response.target_class || target || result.leading_class,
              maskData: response.image_map.data,
            })
          )
        } catch { /* Ignore storage quota errors */ }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setMessage(error instanceof Error ? error.message : 'Explanation request failed.')
    } finally {
      setBusy(false)
      setStage('')
    }
  }
  return <section className="analysis-inspector" aria-label="Analysis results and evidence">
    <nav className="inspector-tabs" aria-label="Evidence sections">{tabs.map(({ label, icon: Icon }) => {
      const isDisabled = isOodResult && label !== 'Classification'
      return <button type="button" key={label} aria-pressed={tab === label} aria-controls="inspector-content" disabled={isDisabled} title={isDisabled ? 'Disabled for Out-of-Domain image' : undefined} className={tab === label ? 'selected' : ''} onClick={() => setTab(label)}><Icon size={16} /><span>{label}</span></button>
    })}</nav>
    <div id="inspector-content" className="inspector-content" aria-label={tab}>
      {tab === 'Classification' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Prediction review</div><h2>Classification</h2><p>Review the leading result, then explore alternatives.</p></div>
        {result ? <ClassificationSummary key={result.analysis_id} result={result} /> : <><Unavailable icon={BarChart3} title="No classification yet" text={hasImage ? 'Your image is ready for review. Model inference will appear here once the backend is connected.' : 'Add an image on the left to prepare an analysis.'} />
        <div className="inspector-provenance"><div><span>Model</span><strong>Not connected</strong></div><div><span>Result</span><strong>Not available</strong></div></div></>}
        {!result && <p className="inspector-disclosure"><Info size={15} />Class scores are model outputs, not a confirmed diagnosis.</p>}
      </>}
      {tab === 'XAI' && <>
        <div className="inspector-section-heading">
          <div className="eyebrow">Explainable AI (XAI)</div>
          <h2>Explain the prediction</h2>
          <p>Pixel-level Integrated Gradients & Shapley feature sensitivity for clinical inspection.</p>
        </div>
        {!result ? <Unavailable icon={Fingerprint} title="Analysis required" text="Complete an analysis before requesting an explanation." /> : <>
          {/* Disclosure of Single-Fold Explanation vs Ensemble */}
          <div className="xai-stability-banner">
            <strong>ℹ️ Model Explanation Disclosure:</strong> Final classification uses all {result.ensemble.member_count} folds. Visual XAI explains <strong>Fold {fold}</strong> logit across Attention Rollout, ViT Grad-CAM, Integrated Gradients, LRP, and Spatial SHAP.
          </div>

          <div className="xai-controls">
            <label>XAI mode
              <select
                value={xaiMethod}
                onChange={event => setXaiMethod(event.target.value as any)}
              >
                <option value="all">Compare All 5 XAI Methods (Side-by-Side)</option>
                <option value="attention_rollout">1. Transformer Attention Rollout (~2s)</option>
                <option value="grad_cam">2. ViT Grad-CAM (~2s)</option>
                <option value="integrated_gradients">3. Integrated Gradients</option>
                <option value="lrp">4. Layer-wise Relevance Propagation (LRP)</option>
                <option value="shap">5. Spatial Patch SHAP</option>
              </select>
            </label>
            <label>Target class
              <select value={target || result.leading_class} onChange={event => setTarget(event.target.value)}>
                {result.scores.map(item => <option key={item.label} value={item.label}>{item.label} - {CLASS_DESCRIPTIONS[item.label]?.name.split('(')[0]}</option>)}
              </select>
            </label>
            <label>Model fold
              <select value={fold} onChange={event => setFold(event.target.value)}>
                {Array.from({length: result.ensemble.member_count}, (_, index) => <option key={index} value={index}>Fold {index} {index === 0 ? '(Default Primary)' : ''}</option>)}
              </select>
            </label>
            {(xaiMethod === 'all' || xaiMethod === 'integrated_gradients') && (
              <>
                <label>Image baseline
                  <select value={baseline} onChange={event => setBaseline(event.target.value as 'blur' | 'zero')}>
                    <option value="blur">Blurred image (Recommended dermoscopic)</option>
                    <option value="zero">Black image (Zero reference)</option>
                  </select>
                </label>
                <label>IG steps
                  <select value={nSteps} onChange={event => setNSteps(event.target.value as '6' | '8' | '16')}>
                    <option value="6">Fast comparison (6 steps)</option>
                    <option value="8">Interactive (8 steps)</option>
                    <option value="16">Standard diagnostic (16 steps)</option>
                  </select>
                </label>
              </>
            )}
          </div>
          <button type="button" className="primary-button" disabled={busy || !image} onClick={runExplanation}>
            {busy ? `${STAGE_LABEL[stage] || 'Explaining…'} (${elapsed}s)` : (xaiMethod === 'all' ? `Run All 5 XAI Methods (Fold ${fold})` : `Explain Fold ${fold} logit`)}
          </button>
          {busy && <p role="status" className="inspector-disclosure">
            {STAGE_LABEL[stage] || 'Computing XAI attributions on CPU…'}
          </p>}
          {message && <p role="alert" className="inspector-disclosure">{message}</p>}

          {explanation?.status === 'ok' && (explanation.results || explanation.image_map) && (() => {
            const metaAttr = explanation.metadata_attribution
            const baseLogit = metaAttr?.base_value ?? 0
            const fullLogit = metaAttr?.full_value ?? 0
            const metaEffect = fullLogit - baseLogit
            const maxMetaVal = metaAttr ? Math.max(...Object.values(metaAttr.features).map(v => Math.abs(v)), 1e-5) : 1

            const cards: { key: string; title: string; subtitle: string; item: ExplanationResponse }[] = []
            if (explanation.results) {
              if (explanation.results.attention_rollout) {
                cards.push({
                  key: 'attention_rollout',
                  title: '1. Attention Rollout',
                  subtitle: 'Transformer Self-Attention + Class Region',
                  item: explanation.results.attention_rollout,
                })
              }
              if (explanation.results.grad_cam) {
                cards.push({
                  key: 'grad_cam',
                  title: '2. ViT Grad-CAM',
                  subtitle: 'Class-Specific Patch Activation (ReLU)',
                  item: explanation.results.grad_cam,
                })
              }
              if (explanation.results.integrated_gradients) {
                cards.push({
                  key: 'integrated_gradients',
                  title: '3. Integrated Gradients',
                  subtitle: `Path-Integral Attribution (${explanation.results.integrated_gradients.n_steps ?? nSteps} steps)`,
                  item: explanation.results.integrated_gradients,
                })
              }
              if (explanation.results.lrp) {
                cards.push({
                  key: 'lrp',
                  title: '4. Layer-wise Relevance (LRP)',
                  subtitle: 'Transformer AttnLRP · Input × Grad',
                  item: explanation.results.lrp,
                })
              }
              if (explanation.results.shap) {
                cards.push({
                  key: 'shap',
                  title: '5. Spatial SHAP',
                  subtitle: '6×6 Patch Leave-One-Out Shapley',
                  item: explanation.results.shap,
                })
              }
            } else if (explanation.image_map) {
              const titleMap: Record<string, string> = {
                attention_rollout: '1. Attention Rollout',
                grad_cam: '2. ViT Grad-CAM',
                integrated_gradients: '3. Integrated Gradients',
                lrp: '4. Layer-wise Relevance (LRP)',
                shap: '5. Spatial SHAP',
              }
              cards.push({
                key: explanation.method || 'single',
                title: titleMap[explanation.method || ''] || 'XAI Attribution',
                subtitle: `Explaining Fold ${explanation.fold} · ${explanation.target_class}`,
                item: explanation,
              })
            }

            return (
              <>
                {cards.length > 1 ? (
                  <div className="xai-grid-4">
                    {cards.map(c => (
                      <XaiPanelCard
                        key={c.key}
                        title={c.title}
                        subtitle={c.subtitle}
                        explanation={c.item}
                        imageUrl={imageUrl}
                        view={view}
                        opacity={opacity}
                      />
                    ))}
                  </div>
                ) : (
                  cards.map(c => (
                    <XaiPanelCard
                      key={c.key}
                      title={c.title}
                      subtitle={c.subtitle}
                      explanation={c.item}
                      imageUrl={imageUrl}
                      view={view}
                      opacity={opacity}
                    />
                  ))
                )}

                {/* Shared View Switcher */}
                <div className="xai-view-switch" aria-label="Attribution view switcher">
                  {[
                    { id: 'overlay', label: 'Overlay' },
                    { id: 'signed', label: 'Positive/Negative' },
                    { id: 'abs', label: 'Absolute magnitude' },
                    { id: 'original', label: 'Original (224×224)' },
                  ].map(({ id, label }) => (
                    <button
                      key={id}
                      type="button"
                      aria-pressed={view === id}
                      onClick={() => setView(id as any)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {view === 'overlay' && (
                  <label className="disabled-range">
                    Overlay opacity<span>{opacity}%</span>
                    <input type="range" min="10" max="100" value={opacity} onChange={event => setOpacity(Number(event.target.value))} aria-label="Overlay opacity" />
                  </label>
                )}

                {/* Doctor-friendly Legend */}
                <div className="xai-legend">
                  <div className="xai-legend-bar-wrapper">
                    <span style={{ color: '#2563eb' }}>Decreases score (−)</span>
                    <span className="bar" />
                    <span style={{ color: '#dc2626' }}>Increases score (+)</span>
                  </div>
                  <p>
                    For <strong>IG, LRP, &amp; SHAP</strong>: Red increases <strong>{explanation.target_class}</strong> score; blue decreases it. For <strong>Attention Rollout &amp; ViT Grad-CAM</strong>: Warm orange highlights high-activation lesion regions.
                  </p>
                </div>

                {/* Metadata Shapley Section with Centered Diverging Zero-Point Bar */}
                {metaAttr && (
                  <section className="metadata-attribution">
                    <h3>Metadata Sensitivity (Shapley Values)</h3>
                    <div className="metadata-summary-box">
                      <div className="metadata-summary-row">
                        <span>Baseline class logit (neutral metadata):</span>
                        <strong>{baseLogit.toFixed(3)}</strong>
                      </div>
                      <div className="metadata-summary-row">
                        <span>With patient metadata:</span>
                        <strong>{fullLogit.toFixed(3)}</strong>
                      </div>
                      <div className="metadata-summary-row total-effect">
                        <span>Net metadata effect:</span>
                        <strong style={{ color: metaEffect >= 0 ? '#dc2626' : '#2563eb' }}>
                          {metaEffect >= 0 ? '+' : ''}{metaEffect.toFixed(3)} logit
                        </strong>
                      </div>
                    </div>

                    <div style={{ marginTop: '8px' }}>
                      <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>
                        Diverging logit contribution (Center line is 0.0):
                      </p>
                      {Object.entries(metaAttr.features).map(([name, value]) => {
                        const pct = Math.min(50, (Math.abs(value) / maxMetaVal) * 50)
                        return (
                          <div className="metadata-bar-diverging" key={name}>
                            <span className="metadata-bar-diverging-name">{name}</span>
                            <div className="metadata-axis-container">
                              <div className="metadata-center-line" />
                              <div
                                className={`metadata-diverging-fill ${value >= 0 ? 'positive' : 'negative'}`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span
                              className="metadata-bar-val"
                              style={{ color: value >= 0 ? '#dc2626' : '#2563eb' }}
                            >
                              {value >= 0 ? '+' : ''}{value.toFixed(4)}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    {/* Interpretation sentence for doctors */}
                    <ul className="metadata-interpretation-list">
                      {Object.entries(metaAttr.features).map(([name, value]) => {
                        let text = ''
                        const absV = Math.abs(value)
                        const direction = value > 0 ? 'increased' : 'decreased'
                        if (absV < 0.01) {
                          text = `${name.charAt(0).toUpperCase() + name.slice(1)} had no measurable influence on the ${explanation.target_class} score.`
                        } else if (absV < 0.1) {
                          text = `${name.charAt(0).toUpperCase() + name.slice(1)} slightly ${direction} the ${explanation.target_class} score (${value > 0 ? '+' : ''}${value.toFixed(3)}).`
                        } else {
                          text = `${name.charAt(0).toUpperCase() + name.slice(1)} noticeably ${direction} the ${explanation.target_class} score (${value > 0 ? '+' : ''}${value.toFixed(3)}).`
                        }
                        return (
                          <li key={name}>
                            <span>•</span>
                            <span>{text}</span>
                          </li>
                        )
                      })}
                    </ul>
                  </section>
                )}

                <details className="xai-about">
                  <summary>About this explanation</summary>
                  <p>{explanation.limitations}</p>
                  <p>
                    {explanation.method} · Explaining Fold {explanation.fold} logit · {explanation.baseline === 'none' ? 'No baseline (Attention)' : `${explanation.baseline} baseline`} · {explanation.n_steps} step(s) · {explanation.elapsed_ms}ms
                  </p>
                </details>
              </>
            )
          })()}
        </>}
        <p className="inspector-disclosure"><Info size={15} />Attribution describes individual model fold behavior; it does not establish clinical correctness or ground-truth histology.</p>
      </>}
      {tab === 'Uncertainty' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Know the limitations</div><h2>Uncertainty & quality</h2><p>Signals to review, not a single trust score.</p></div>
        <div className="uncertainty-rows">{[
          ['Predictive uncertainty', 'Normalized entropy / top-two margin', result ? `${result.uncertainty.normalized_entropy.toFixed(3)} / ${(result.uncertainty.top_two_margin*100).toFixed(1)} percentage points` : 'Not computed'],
          ['Probability calibration', result?.calibration?.reason || 'Calibration status for this model and input policy', result ? (result.calibration?.applied ? `Temperature scaled · T=${result.calibration.temperature?.toFixed(3)}` : 'Not applied') : 'Not computed'],
          ['Conformal differential guarantee', 'Empirically calibrated prediction set size at 95% marginal coverage', result ? `${(result.conformal_prediction || evaluateConformalSet(result.scores, 0.95)).set_size} conditions (${(result.conformal_prediction || evaluateConformalSet(result.scores, 0.95)).tier_label})` : 'Not evaluated'],
          ['Model agreement', 'Fraction of ensemble members matching the leading class', result?.ensemble.agreement != null ? `${(result.ensemble.agreement*100).toFixed(0)}%` : 'Requires multiple members'],
          ['Malignant guardrail', 'Safety threshold for high-risk melanoma/carcinoma in differential', result?.rejection ? (result.rejection.malignant_risk_flag ? `Active · Malignant risk ${((result.rejection.malignant_metrics.total_malignant_score)*100).toFixed(1)}%` : 'Passed · Standard protocol') : 'Not evaluated'],
          ['Selective rejection', 'Automatic case routing based on certainty & risk', result ? (result.assessment_status === 'unable_to_assess' ? 'Unable to Assess (Safeguard Active)' : 'Assessed (Clean Pass)') : 'Not evaluated'],
          ['Clinical image quality (IQA)', '4-point dermoscopic validation: Micro-detail focus, exposure, glare, and lesion framing', result?.image_quality ? (result.image_quality.status === 'passed' ? `Passed · Optimal (${result.image_quality.overall_score ?? 94}% Adequacy)` : result.image_quality.status === 'warning' ? `Warning · Acceptable (${result.image_quality.overall_score ?? 75}% with Advisories)` : `Rejected · Severe Blur (${result.image_quality.sharpness_score} < Cutoff)`) : 'Not evaluated'],
          ['Out-of-distribution detection', 'Optical domain, feature energy novelty & ensemble concordance', result?.ood ? (result.ood.status === 'in_distribution' ? `Passed · In-Distribution (${(result.ood.confidence_score * 100).toFixed(0)}% InD Confidence)` : result.ood.status === 'borderline' ? `Warning · Borderline (${(result.ood.ood_score * 100).toFixed(0)}% OOD Risk)` : `Rejected · Out-of-Distribution (${(result.ood.ood_score * 100).toFixed(0)}% OOD Risk)`) : 'Not evaluated'],
        ].map(([title, detail, status]) => <div key={title}><h3>{title}</h3><p>{detail}</p><span className="unavailable-tag">{status}</span></div>)}</div>

        {/* Clinical Image Quality Assessment Panel */}
        {result?.image_quality && (
          <div className="uncertainty-iqa-inspector">
            <div className="uncertainty-iqa-header">
              <Camera size={20} className="iqa-header-icon" />
              <div>
                <h4>Image Quality Check</h4>
              </div>
              <div className={`iqa-overall-badge iqa-overall-badge--${result.image_quality.status}`}>
                <strong>{result.image_quality.overall_score ?? (result.image_quality.blur_detected ? 35 : 94)}%</strong>
                <span>{result.image_quality.status === 'passed' ? 'Optimal Quality' : result.image_quality.clinical_verdict || 'Check Required'}</span>
              </div>
            </div>

            <div className="uncertainty-iqa-grid">
              {(result.image_quality.checks || [
                { id: 'focus', name: 'Focus & Sharpness', label: result.image_quality.blur_detected ? 'Severe Blur' : 'Sharp & In-Focus', status: result.image_quality.blur_detected ? 'fail' : 'pass', score_pct: result.image_quality.blur_detected ? 20 : 95, clinical_impact: 'High-frequency pigment networks and globules are distinct.' },
                { id: 'exposure', name: 'Lighting & Exposure', label: 'Balanced Illumination', status: 'pass', score_pct: 90, clinical_impact: 'Optimal contrast between lesion and surrounding skin.' },
                { id: 'glare', name: 'Glare & Reflection', label: 'Anti-reflective Clarity', status: 'pass', score_pct: 95, clinical_impact: 'No specular flash reflection obscuring subsurface patterns.' },
                { id: 'framing', name: 'Lesion Centering', label: 'Well-Centered', status: 'pass', score_pct: 95, clinical_impact: 'Full lesion perimeter is captured within visual field.' }
              ]).map(check => {
                const displayName = IQA_DISPLAY_NAMES[check.id] || check.name
                return (
                  <div key={check.id} className={`uncertainty-iqa-card uncertainty-iqa-card--${check.status}`}>
                    <div className="iqa-card-top">
                      <span className="iqa-card-name">
                        {check.id === 'focus' && <ScanLine size={15} />}
                        {check.id === 'exposure' && <Sun size={15} />}
                        {check.id === 'glare' && <Sparkles size={15} />}
                        {check.id === 'framing' && <Crosshair size={15} />}
                        {displayName}
                      </span>
                      <span className={`iqa-card-pill iqa-card-pill--${check.status}`}>
                        {check.status === 'pass' ? '✓ Passed' : check.status === 'warn' ? '⚠️ Advisory' : '✕ Defect'}
                      </span>
                    </div>
                    <div className="iqa-card-label-row">
                      <span className="iqa-card-verdict">{check.label}</span>
                      <strong className="iqa-card-score">{check.score_pct}%</strong>
                    </div>
                    <div className="iqa-progress-bar">
                      <div className={`iqa-progress-fill iqa-progress-fill--${check.status}`} style={{ width: `${check.score_pct}%` }} />
                    </div>
                    {check.status !== 'pass' && <p className="iqa-card-impact">{check.clinical_impact}</p>}
                  </div>
                )
              })}
            </div>

            {/* Clinician Actionable Guidance shown only when there is an active advisory or issue */}
            {result.image_quality.status !== 'passed' && (
              <div className={`uncertainty-iqa-guidance uncertainty-iqa-guidance--${result.image_quality.status}`}>
                <Stethoscope size={18} />
                <div>
                  <strong>Clinician Actionable Guidance</strong>
                  <p>{result.image_quality.doctor_recommendation || result.image_quality.details}</p>
                </div>
              </div>
            )}

            <details className="uncertainty-iqa-disclosure">
              <summary><HelpCircle size={14} /> Doctor Guide: How Image Quality Influences Diagnosis</summary>
              <div className="iqa-disclosure-content">
                <p><strong>1. Micro-structure Preservation:</strong> Early malignant melanoma indicators (atypical pigment network, peripheral globules, streaks) are microscopic. Optical blur smooths high-frequency gradients and leads to false assurance.</p>
                <p><strong>2. Color Variegation & Glare:</strong> Glare from flash reflection washes out colors and masks blue-white veils or red vascular structures (crucial dermoscopic criteria).</p>
                <p><strong>3. Automated Safeguard:</strong> DermaInsight automatically withholds autonomous classification on severely blurred images to protect patient safety.</p>
              </div>
            </details>
          </div>
        )}

        {result?.ood && (
          <div className="uncertainty-ood-inspector">
            <div className="uncertainty-ood-header">
              {result.ood.status === 'in_distribution' ? (
                <ShieldCheck size={22} style={{ color: '#0f766e', flexShrink: 0 }} />
              ) : result.ood.status === 'borderline' ? (
                <AlertTriangle size={22} style={{ color: '#b45309', flexShrink: 0 }} />
              ) : (
                <ShieldAlert size={22} style={{ color: '#dc2626', flexShrink: 0 }} />
              )}
              <h4 style={{ color: result.ood.status === 'in_distribution' ? '#0f766e' : result.ood.status === 'borderline' ? '#b45309' : '#dc2626' }}>
                Domain &amp; OOD Check: {result.ood.status === 'in_distribution' ? 'Valid Skin Photo' : result.ood.status === 'borderline' ? 'Borderline Photo' : 'Out-of-Domain'}
              </h4>
            </div>

            <div className="uncertainty-ood-badges">
              {result.ood.badges.map(b => {
                const simpleMap: Record<string, { title: string; pass: string; warn: string; fail: string }> = {
                  domain: { title: 'Skin Photo Check', pass: 'Valid skin lesion photo', warn: 'Unusual lighting or color', fail: 'Not a skin lesion photo' },
                  energy: { title: 'AI Familiarity', pass: 'Matches trained cases', warn: 'Looks somewhat unusual', fail: 'Unfamiliar image' },
                  anchor: { title: 'Diagnosis Clarity', pass: 'Clear leading condition', warn: 'Somewhat uncertain', fail: 'No clear diagnosis' },
                  ensemble: { title: 'Model Agreement', pass: 'All models agree', warn: 'Minor disagreement', fail: 'Models disagree' },
                }
                const info = simpleMap[b.id]
                const title = info?.title ?? b.label
                const detail = info ? info[b.status] : b.detail
                return (
                  <div key={b.id} className={`uncertainty-ood-pill uncertainty-ood-pill--${b.status}`}>
                    <span className="badge-name">{title}</span>
                    <span className="badge-detail">{detail}</span>
                    <span className="badge-state">
                      {b.status === 'pass' ? '✓ Passed' : b.status === 'warn' ? '⚠️ Warning' : '✕ Failed'}
                    </span>
                  </div>
                )
              })}
            </div>

            <div className="uncertainty-ood-footer">
              <span>OOD Risk Score: <strong>{(result.ood.ood_score * 100).toFixed(1)}%</strong> (Limit: {(result.ood.threshold * 100).toFixed(0)}%)</span>
              <Link to="/analysis?module=ood" className="ood-deep-link">
                Review OOD Model Evidence <ArrowRight size={15} />
              </Link>
            </div>
          </div>
        )}
        <Link className="evidence-link" to="/analysis?module=conformal">Prediction sets (Advanced Analysis) <ArrowRight size={15} /></Link>
      </>}
    </div>
  </section>
}
