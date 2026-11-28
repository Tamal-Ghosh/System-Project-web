import { AlertTriangle, CheckCircle2, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getCalibrationEvidence } from '../../services/calibration'
import type { CalibrationEvidence as Evidence } from '../../services/calibration'

function ReliabilityDiagram({ evidence }: { evidence: Evidence }) {
  const size = 420
  const padding = 44
  const inner = size - padding * 2
  const point = (value: number) => padding + value * inner
  const points = evidence.reliability_bins
    .map(bin => `${point(bin.confidence)},${size - point(bin.accuracy)}`)
    .join(' ')

  return <div className="calibration-chart-card" style={{ width: '100%', boxSizing: 'border-box' }}>
    <div className="calibration-card-heading" style={{ marginBottom: '14px' }}>
      <div>
        <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Reliability diagram</h3>
        <p style={{ fontSize: '13.5px' }}>Mean confidence compared with observed accuracy</p>
      </div>
      <span>OOF validation</span>
    </div>
    <div style={{ display: 'flex', justifyContent: 'center', width: '100%', margin: '12px 0' }}>
      <svg
        className="reliability-chart"
        viewBox={`0 0 ${size} ${size}`}
        style={{ width: 'min(100%, 540px)', height: 'auto', display: 'block', overflow: 'visible' }}
        role="img"
        aria-label="Reliability diagram comparing model confidence with observed accuracy"
      >
        {[0, .25, .5, .75, 1].map(value => <g key={value}>
          <line x1={point(value)} y1={padding} x2={point(value)} y2={size - padding} className="chart-grid" stroke="#e8edf2" strokeWidth={1} />
          <line x1={padding} y1={size - point(value)} x2={size - padding} y2={size - point(value)} className="chart-grid" stroke="#e8edf2" strokeWidth={1} />
          <text x={point(value)} y={size - 18} textAnchor="middle" fill="#70859a" fontSize="11px">{Math.round(value * 100)}</text>
          <text x={26} y={size - point(value) + 4} textAnchor="middle" fill="#70859a" fontSize="11px">{Math.round(value * 100)}</text>
        </g>)}
        <line x1={padding} y1={size - padding} x2={size - padding} y2={padding} className="chart-reference" stroke="#aebcc9" strokeWidth={1.5} strokeDasharray="5 5" />
        <polyline points={points} className="chart-series" fill="none" stroke="#008e82" strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
        {evidence.reliability_bins.map(bin => <circle key={bin.lower} cx={point(bin.confidence)} cy={size - point(bin.accuracy)} r="5.5" className="chart-point" fill="white" stroke="#008e82" strokeWidth={2.5}><title>{`${Math.round(bin.lower * 100)}–${Math.round(bin.upper * 100)}% · n=${bin.count}`}</title></circle>)}
        <text x={size / 2} y={size - 1} textAnchor="middle" className="chart-axis-title" fill="#70859a" fontSize="12px" fontWeight={650}>Confidence (%)</text>
        <text x={-size / 2} y={12} textAnchor="middle" transform="rotate(-90)" className="chart-axis-title" fill="#70859a" fontSize="12px" fontWeight={650}>Accuracy (%)</text>
      </svg>
    </div>
    <div className="chart-legend" style={{ marginTop: '16px', display: 'flex', justifyContent: 'center', gap: '24px', fontSize: '13px' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px' }}><i className="legend-model" style={{ width: '22px', height: '3px', background: '#008e82', display: 'inline-block' }} />Measured</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px' }}><i className="legend-reference" style={{ width: '22px', borderTop: '2px dashed #aebcc9', display: 'inline-block' }} />Ideal agreement</span>
    </div>
  </div>
}

export function CalibrationPanel({ hideLimitations = false }: { hideLimitations?: boolean } = {}) {
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

  return <div className="calibration-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
    <div className="calibration-summary">
      <div className="calibration-metric"><span>Top-label ECE</span><strong>{(evidence.metrics.top_label_ece * 100).toFixed(2)}%</strong><small>Lower is better</small></div>
      <div className="calibration-metric"><span>Multiclass Brier</span><strong>{evidence.metrics.brier_score.toFixed(3)}</strong><small>Lower is better</small></div>
      <div className="calibration-metric"><span>Evaluated images</span><strong>{evidence.sample_count.toLocaleString()}</strong><small>{evidence.class_count} classes</small></div>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <ReliabilityDiagram evidence={evidence} />
      <div className="calibration-method-card" style={{ width: '100%', boxSizing: 'border-box' }}>
        <div className="calibration-card-heading"><div><h3>What was measured</h3><p>{evidence.model_family}</p></div><CheckCircle2 size={20} /></div>
        <dl className="calibration-details"><div><dt>Evaluation scope</dt><dd>{evidence.scope}</dd></div><div><dt>Evidence type</dt><dd>Model-level, out-of-fold · paired images</dd></div><div><dt>Live score scaling</dt><dd>{evidence.temperature_scaling.applied ? `Applied · T=${evidence.temperature_scaling.temperature?.toFixed(3)}` : 'Not applied'}</dd></div></dl>
        {evidence.temperature_scaling.applied && <div className="temperature-notice temperature-notice--active"><CheckCircle2 size={18} /><div><strong>Temperature scaling active</strong><p>{evidence.temperature_scaling.reason}</p></div></div>}
      </div>
    </div>
    {!hideLimitations && (
      <div className="calibration-limitations"><h3>Interpret with care</h3><ul>{evidence.limitations.map(item => <li key={item}>{item}</li>)}</ul></div>
    )}
  </div>
}
