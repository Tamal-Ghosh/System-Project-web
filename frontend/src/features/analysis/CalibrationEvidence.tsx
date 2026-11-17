import { AlertTriangle, CheckCircle2, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getCalibrationEvidence } from '../../services/calibration'
import type { CalibrationEvidence as Evidence } from '../../services/calibration'

function ReliabilityDiagram({ evidence }: { evidence: Evidence }) {
  const size = 280
  const padding = 34
  const inner = size - padding * 2
  const point = (value: number) => padding + value * inner
  const points = evidence.reliability_bins
    .map(bin => `${point(bin.confidence)},${size - point(bin.accuracy)}`)
    .join(' ')

  return <div className="calibration-chart-card">
    <div className="calibration-card-heading"><div><h3>Reliability diagram</h3><p>Mean confidence compared with observed accuracy</p></div><span>OOF validation</span></div>
    <svg className="reliability-chart" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Reliability diagram comparing model confidence with observed accuracy">
      {[0, .25, .5, .75, 1].map(value => <g key={value}>
        <line x1={point(value)} y1={padding} x2={point(value)} y2={size - padding} className="chart-grid" />
        <line x1={padding} y1={size - point(value)} x2={size - padding} y2={size - point(value)} className="chart-grid" />
        <text x={point(value)} y={size - 12} textAnchor="middle">{Math.round(value * 100)}</text>
        <text x={21} y={size - point(value) + 4} textAnchor="middle">{Math.round(value * 100)}</text>
      </g>)}
      <line x1={padding} y1={size - padding} x2={size - padding} y2={padding} className="chart-reference" />
      <polyline points={points} className="chart-series" />
      {evidence.reliability_bins.map(bin => <circle key={bin.lower} cx={point(bin.confidence)} cy={size - point(bin.accuracy)} r="4.5" className="chart-point"><title>{`${Math.round(bin.lower * 100)}–${Math.round(bin.upper * 100)}% · n=${bin.count}`}</title></circle>)}
      <text x={size / 2} y={size - 1} textAnchor="middle" className="chart-axis-title">Confidence (%)</text>
      <text x={-size / 2} y={9} textAnchor="middle" transform="rotate(-90)" className="chart-axis-title">Accuracy (%)</text>
    </svg>
    <div className="chart-legend"><span><i className="legend-model" />Measured</span><span><i className="legend-reference" />Ideal agreement</span></div>
  </div>
}

export function CalibrationPanel() {
  const [evidence, setEvidence] = useState<Evidence | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    getCalibrationEvidence(controller.signal).then(setEvidence).catch(error => {
      if (error?.name !== 'AbortError') setError(error instanceof Error ? error.message : 'Calibration evidence is unavailable.')
    })
    return () => controller.abort()
  }, [])

  if (error) return <div className="advanced-unavailable"><AlertTriangle size={28} /><h3>Calibration evidence unavailable</h3><p>{error}</p><span className="unavailable-tag">Backend not connected</span></div>
  if (!evidence) return <div className="calibration-loading"><LoaderCircle size={22} className="spin" />Loading measured evidence…</div>

  return <div className="calibration-panel">
    <div className="calibration-summary">
      <div className="calibration-metric"><span>Top-label ECE</span><strong>{(evidence.metrics.top_label_ece * 100).toFixed(2)}%</strong><small>Lower is better</small></div>
      <div className="calibration-metric"><span>Multiclass Brier</span><strong>{evidence.metrics.brier_score.toFixed(3)}</strong><small>Lower is better</small></div>
      <div className="calibration-metric"><span>Evaluated images</span><strong>{evidence.sample_count.toLocaleString()}</strong><small>{evidence.class_count} classes</small></div>
    </div>
    <div className="calibration-grid">
      <ReliabilityDiagram evidence={evidence} />
      <div className="calibration-method-card">
        <div className="calibration-card-heading"><div><h3>What was measured</h3><p>{evidence.model_family}</p></div><CheckCircle2 size={20} /></div>
        <dl className="calibration-details"><div><dt>Evaluation scope</dt><dd>{evidence.scope}</dd></div><div><dt>Evidence type</dt><dd>Model-level, out-of-fold</dd></div><div><dt>Live score scaling</dt><dd>{evidence.temperature_scaling.applied ? `Applied · T=${evidence.temperature_scaling.temperature?.toFixed(3)}` : 'Not applied'}</dd></div></dl>
        {evidence.temperature_scaling.applied ? <div className="temperature-notice temperature-notice--active"><CheckCircle2 size={18} /><div><strong>Temperature scaling active</strong><p>{evidence.temperature_scaling.reason}</p></div></div> : <div className="temperature-notice"><AlertTriangle size={18} /><div><strong>Temperature scaling unavailable</strong><p>{evidence.temperature_scaling.reason}</p></div></div>}
      </div>
    </div>
    <div className="calibration-limitations"><h3>Interpret with care</h3><ul>{evidence.limitations.map(item => <li key={item}>{item}</li>)}</ul></div>
  </div>
}
