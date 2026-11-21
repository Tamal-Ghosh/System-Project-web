import type { ClassificationResult, ExplanationResponse } from '../../services/classification'
import { useEffect, useRef, useState } from 'react'
import { BarChart3, ScanLine, ShieldQuestion, ArrowRight, Info, Fingerprint } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

const tabs: { label: string; icon: LucideIcon }[] = [
  { label: 'Classification', icon: BarChart3 }, { label: 'XAI', icon: ScanLine },
  { label: 'Uncertainty', icon: ShieldQuestion },
]

function Unavailable({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return <div className="inspector-empty"><div className="inspector-empty-icon"><Icon size={25} strokeWidth={1.5} /></div><h3>{title}</h3><p>{text}</p></div>
}

export function AnalysisInspector({ hasImage, result, image, age, sex, site }: { hasImage: boolean; result?: ClassificationResult; image?: Blob; age?: string; sex?: string; site?: string }) {
  const [tab, setTab] = useState('Classification')
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [stage, setStage] = useState('')
  const [target, setTarget] = useState('')
  const [fold, setFold] = useState('0')
  const [baseline, setBaseline] = useState<'blur' | 'zero'>('blur')
  const [opacity, setOpacity] = useState(55)
  const [view, setView] = useState<'overlay' | 'original' | 'heatmap'>('overlay')
  const [startedAt, setStartedAt] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [imageUrl, setImageUrl] = useState('')
  const explanationController = useRef<AbortController | null>(null)
  useEffect(() => { if (!image) { setImageUrl(''); return }; const url = URL.createObjectURL(image); setImageUrl(url); return () => URL.revokeObjectURL(url) }, [image])
  useEffect(() => { explanationController.current?.abort(); setExplanation(null); setMessage(''); setTarget(result?.leading_class ?? ''); return () => explanationController.current?.abort() }, [image, age, sex, site, result])
  useEffect(() => { if (!busy) return; const timer = window.setInterval(() => setElapsed(Math.floor((Date.now()-startedAt)/1000)), 250); return () => window.clearInterval(timer) }, [busy, startedAt])
  const STAGE_LABEL: Record<string, string> = {
    queued: 'Waiting in queue…',
    integrated_gradients: 'Calculating Integrated Gradients…',
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
        baseline, nSteps: 5, includeMetadata: true, signal: controller.signal
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
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setMessage(error instanceof Error ? error.message : 'Explanation request failed.')
    } finally {
      setBusy(false)
      setStage('')
    }
  }
  return <section className="analysis-inspector" aria-label="Analysis results and evidence">
    <nav className="inspector-tabs" aria-label="Evidence sections">{tabs.map(({ label, icon: Icon }) => <button type="button" key={label} aria-pressed={tab === label} aria-controls="inspector-content" className={tab === label ? 'selected' : ''} onClick={() => setTab(label)}><Icon size={16} /><span>{label}</span></button>)}</nav>
    <div id="inspector-content" className="inspector-content" aria-label={tab}>
      {tab === 'Classification' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Model output</div><h2>Classification</h2><p>Start with the result. Inspect the evidence.</p></div>
        {result ? <div className="classification-results"><h3>{result.leading_class}</h3>
          <p>Leading model score: {((result.scores.find(item => item.label === result.leading_class)?.score ?? 0)*100).toFixed(1)}%</p>
          {[...result.scores].sort((a,b) => b.score-a.score).map(item => <div className="class-score" key={item.label}><span>{item.label}</span><progress value={item.score} max={1} aria-label={`${item.label} model score`} /><strong>{(item.score*100).toFixed(1)}%</strong></div>)}
          <div className="inspector-provenance"><div><span>Model</span><strong>{result.model_version}</strong></div><div><span>Members / TTA</span><strong>{result.ensemble.member_count} / {result.tta ? 'On' : 'Off'}</strong></div><div><span>Storage</span><strong>Not saved</strong></div></div>
          {result.limitations.map(text => <p className="inspector-disclosure" key={text}><Info size={15} />{text}</p>)}
        </div> : <><Unavailable icon={BarChart3} title="No classification yet" text={hasImage ? 'Your image is ready for review. Model inference will appear here once the backend is connected.' : 'Add an image on the left to prepare an analysis.'} />
        <div className="inspector-provenance"><div><span>Model</span><strong>Not connected</strong></div><div><span>Result</span><strong>Not available</strong></div></div></>}
        <p className="inspector-disclosure"><Info size={15} />Class scores are model outputs, not a confirmed diagnosis.</p>
      </>}
      {tab === 'XAI' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Inspect the basis</div><h2>Explain the prediction</h2><p>Keep the original image in view.</p></div>
        {!result ? <Unavailable icon={Fingerprint} title="Analysis required" text="Complete an analysis before requesting an explanation." /> : <>
          <div className="xai-controls">
            <label>Target class<select value={target || result.leading_class} onChange={event => setTarget(event.target.value)}>{result.scores.map(item => <option key={item.label}>{item.label}</option>)}</select></label>
            <label>Fold<select value={fold} onChange={event => setFold(event.target.value)}>{Array.from({length: result.ensemble.member_count}, (_, index) => <option key={index} value={index}>Fold {index}</option>)}</select></label>
            <label>Image baseline<select value={baseline} onChange={event => setBaseline(event.target.value as 'blur' | 'zero')}><option value="blur">Blurred image</option><option value="zero">Black image</option></select></label>
          </div>
          <button type="button" className="primary-button" disabled={busy || !image} onClick={runExplanation}>
            {busy ? `${STAGE_LABEL[stage] || 'Explaining…'} (${elapsed}s)` : 'Explain'}
          </button>
          {busy && <p role="status" className="inspector-disclosure">Computing Integrated Gradients on CPU (5 steps). Progress: {STAGE_LABEL[stage] || 'running'}.</p>}
          {message && <p role="alert" className="inspector-disclosure">{message}</p>}
          {explanation?.status === 'ok' && explanation.image_map && <>
            <div className="xai-preview" data-view={view}>
              {view !== 'heatmap' && imageUrl && <img src={imageUrl} alt="Classified image crop" />}
              {view !== 'original' && <div role="img" aria-label="Integrated Gradients attribution heatmap" className="xai-heatmap" style={{opacity: view === 'heatmap' ? 1 : opacity/100, maskImage:`url(data:image/png;base64,${explanation.image_map.data})`, WebkitMaskImage:`url(data:image/png;base64,${explanation.image_map.data})`}} />}
            </div>
            <div className="xai-view-switch" aria-label="Heatmap view">{(['original','overlay','heatmap'] as const).map(value => <button key={value} type="button" aria-pressed={view===value} onClick={() => setView(value)}>{value === 'original' ? 'Original' : value === 'heatmap' ? 'Heatmap' : 'Overlay'}</button>)}</div>
            <label className="disabled-range">Overlay opacity<span>{opacity}%</span><input type="range" min="0" max="100" value={opacity} onChange={event => setOpacity(Number(event.target.value))} aria-label="Overlay opacity" /></label>
            <div className="xai-legend"><span />Higher = more influence on the selected class score</div>
            {explanation.metadata_attribution && <section className="metadata-attribution"><h3>Metadata sensitivity</h3><p>Base {explanation.metadata_attribution.base_value.toFixed(3)} · Full {explanation.metadata_attribution.full_value.toFixed(3)}</p>{Object.entries(explanation.metadata_attribution.features).map(([name, value]) => <div className="metadata-bar" key={name}><span>{name}</span><div><i className={value < 0 ? 'negative' : ''} style={{width:`${Math.min(100,Math.abs(value)*30)}%`}} /></div><strong>{value >= 0 ? '+' : ''}{value.toFixed(4)}</strong></div>)}</section>}
            <details className="xai-about"><summary>About this explanation</summary><p>{explanation.limitations}</p><p>{explanation.method} · {explanation.score} · Fold {explanation.fold} · {explanation.baseline} baseline · {explanation.n_steps} steps · TTA {explanation.tta} · convergence delta {explanation.convergence_delta?.toExponential(2)}</p></details>
          </>}
        </>}
        <p className="inspector-disclosure"><Info size={15} />Attribution describes model behavior; it does not establish clinical correctness.</p>
      </>}
      {tab === 'Uncertainty' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Know the limitations</div><h2>Uncertainty & quality</h2><p>Signals to review, not a single trust score.</p></div>
        <div className="uncertainty-rows">{[
          ['Predictive uncertainty', 'Normalized entropy / top-two margin', result ? `${result.uncertainty.normalized_entropy.toFixed(3)} / ${(result.uncertainty.top_two_margin*100).toFixed(1)} percentage points` : 'Not computed'],
          ['Model agreement', 'Fraction of ensemble members matching the leading class', result?.ensemble.agreement != null ? `${(result.ensemble.agreement*100).toFixed(0)}%` : 'Requires multiple members'],
          ['Image quality', 'Blur, glare and framing checks', 'Not checked'],
          ['Out-of-distribution', 'Compatibility with the input domain', 'Not evaluated'],
        ].map(([title, detail, status]) => <div key={title}><h3>{title}</h3><p>{detail}</p><span className="unavailable-tag">{status}</span></div>)}</div>
        <Link className="evidence-link" to="/analysis?module=calibration">Calibration & validation evidence <ArrowRight size={15} /></Link>
      </>}
    </div>
    <footer className="inspector-footer"><Link to="/analysis?module=calibration">Advanced analysis & model evidence<ArrowRight size={14} /></Link></footer>
  </section>
}
