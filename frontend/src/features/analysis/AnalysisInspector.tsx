import { useState } from 'react'
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

export function AnalysisInspector({ hasImage }: { hasImage: boolean }) {
  const [tab, setTab] = useState('Classification')
  const [method, setMethod] = useState('Grad-CAM')
  return <section className="analysis-inspector" aria-label="Analysis results and evidence">
    <nav className="inspector-tabs" aria-label="Evidence sections">{tabs.map(({ label, icon: Icon }) => <button type="button" key={label} aria-pressed={tab === label} aria-controls="inspector-content" className={tab === label ? 'selected' : ''} onClick={() => setTab(label)}><Icon size={16} /><span>{label}</span></button>)}</nav>
    <div id="inspector-content" className="inspector-content" aria-label={tab}>
      {tab === 'Classification' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Model output</div><h2>Classification</h2><p>Start with the result. Inspect the evidence.</p></div>
        <Unavailable icon={BarChart3} title="No classification yet" text={hasImage ? 'Your image is ready for review. Model inference will appear here once the backend is connected.' : 'Add an image on the left to prepare an analysis.'} />
        <div className="inspector-provenance"><div><span>Model</span><strong>Not connected</strong></div><div><span>Result</span><strong>Not available</strong></div></div>
        <p className="inspector-disclosure"><Info size={15} />Class scores are model outputs, not a confirmed diagnosis.</p>
      </>}
      {tab === 'XAI' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Inspect the basis</div><h2>Explain the prediction</h2><p>Keep the original image in view.</p></div>
        <div className="method-switch" aria-label="Explanation method">{['Grad-CAM', 'SHAP'].map(value => <button key={value} type="button" aria-pressed={method === value} className={method === value ? 'selected' : ''} onClick={() => setMethod(value)}>{value}</button>)}</div>
        <Unavailable icon={Fingerprint} title={`${method} is not available`} text="An explanation needs a completed analysis and a connected explanation service. No heatmap has been generated." />
        <label className="disabled-range">Overlay opacity<span>Not available</span><input type="range" min="0" max="100" disabled aria-label="Overlay opacity — no explanation available" /></label>
        <p className="inspector-disclosure"><Info size={15} />Attribution describes model behaviour; it does not prove clinical correctness.</p>
      </>}
      {tab === 'Uncertainty' && <>
        <div className="inspector-section-heading"><div className="eyebrow">Know the limitations</div><h2>Uncertainty & quality</h2><p>Signals to review, not a single trust score.</p></div>
        <div className="uncertainty-rows">{[
          ['Predictive uncertainty', 'Entropy and top-two margin', 'Not computed'],
          ['Image quality', 'Blur, glare and framing checks', 'Not checked'],
          ['Out-of-distribution', 'Compatibility with the input domain', 'Not evaluated'],
        ].map(([title, detail, status]) => <div key={title}><h3>{title}</h3><p>{detail}</p><span className="unavailable-tag">{status}</span></div>)}</div>
        <Link className="evidence-link" to="/analysis?module=calibration">Calibration & validation evidence <ArrowRight size={15} /></Link>
      </>}
    </div>
    <footer className="inspector-footer"><Link to="/analysis?module=calibration">Advanced analysis & model evidence<ArrowRight size={14} /></Link></footer>
  </section>
}
