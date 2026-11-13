import { ArrowLeft, BarChart3, ImageOff, Info } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAnalysisSession } from './AnalysisSession'
import { regionBounds } from './image/geometry'

const modules = [
  { id: 'calibration', label: 'Calibration', scope: 'Model-level evidence', description: 'Reliability diagram, expected calibration error and Brier score.', requirement: 'Requires held-out calibration data and an evaluated final inference pipeline.' },
  { id: 'validation', label: 'Validation', scope: 'Model-level evidence', description: 'Class-wise performance, dataset details and documented limitations.', requirement: 'Requires measured test-set results, sample counts and evaluation provenance.' },
  { id: 'comparison', label: 'Model comparison', scope: 'Case-level experiment', description: 'Individual model outputs, ensemble results and agreement.', requirement: 'Requires connected model checkpoints and a completed analysis of the selected image.' },
  { id: 'crop', label: 'Crop sensitivity', scope: 'Case-level experiment', description: 'Compare predictions across selected input regions.', requirement: 'Requires saved crop versions and actual classification outputs for each input.' },
  { id: 'stability', label: 'Prediction stability', scope: 'Case-level experiment', description: 'Inspect output changes across explicitly tested image variations.', requirement: 'Requires a connected inference service and a defined transformation protocol.' },
  { id: 'conformal', label: 'Prediction sets', scope: 'Case-level experiment', description: 'Inspect conformal prediction sets and coverage assumptions.', requirement: 'Requires an evaluated conformal method and appropriate calibration data.' },
  { id: 'segmentation', label: 'Segmentation', scope: 'Case-level experiment', description: 'Review lesion boundaries and correction history.', requirement: 'Requires a connected segmentation model and evaluated input handling.' },
  { id: 'subgroups', label: 'Subgroup & external', scope: 'Model-level evidence', description: 'Explore subgroup performance and independent validation.', requirement: 'Requires sufficiently supported subgroup results and verified independent evaluation data.' },
] as const

export function AnalysisPage() {
  const [params, setParams] = useSearchParams()
  const module = modules.find(item => item.id === params.get('module')) ?? modules[0]
  const { image, region } = useAnalysisSession()
  const bounds = image && region ? regionBounds(region, image.width, image.height) : null
  return <div className="advanced-analysis-page">
    <div className="clinical-page-heading"><div><div className="eyebrow">Technical evidence</div><h1>Advanced analysis</h1></div><Link to="/dashboard" className="button button--secondary"><ArrowLeft size={15} />Back to dashboard</Link></div>
    <div className="advanced-context">{image ? <><img src={image.src} alt="Current uploaded image" /><div><strong>{image.name}</strong><span>{bounds ? `${bounds.width} × ${bounds.height} px selected region` : `${image.width} × ${image.height} px · full image`} · retained in this session</span></div></> : <><ImageOff size={20} /><span>No image selected. Model-level evidence can be reviewed independently.</span></>}</div>
    <div className="advanced-layout"><nav className="advanced-modules" aria-label="Advanced analysis modules">{modules.map(item => {
      const isSelected = module.id === item.id
      return <button type="button" key={item.id} aria-pressed={isSelected} aria-controls="advanced-content" className={isSelected ? 'selected' : ''} onClick={() => setParams({ module: item.id })}>
        <span className="module-nav-label">{item.label}</span>
        <span className="module-nav-pill">{isSelected ? 'Active' : ''}</span>
      </button>
    })}</nav>
      <section id="advanced-content" className="advanced-content" aria-label={module.label}><div className="eyebrow">{module.scope}</div><h2>{module.label}</h2><p className="muted">{module.description}</p><div className="advanced-unavailable"><BarChart3 size={28} strokeWidth={1.3} /><h3>No measured output available</h3><p>{module.requirement}</p><span className="unavailable-tag">Not connected</span></div><p className="inspector-disclosure"><Info size={15} />{module.scope === 'Model-level evidence' ? 'These results describe model evaluation; they are not a diagnosis for the current image.' : 'Case experiments use the selected image context; no experiment or clinical measurement has run.'}</p></section>
    </div>
  </div>
}
