import { ChevronDown } from 'lucide-react'
import type { ClassificationResult } from '../../services/classification'
import './classification-summary.css'

const names: Record<string,string> = {
  AKIEC:'Actinic keratosis / intraepidermal carcinoma', BCC:'Basal cell carcinoma',
  BEN_OTH:'Other benign proliferations', BKL:'Benign keratinocytic lesions', DF:'Dermatofibroma',
  INF:'Inflammatory / infectious conditions', MAL_OTH:'Other malignant proliferations',
  MEL:'Melanoma', NV:'Melanocytic nevus', SCCKA:'Squamous cell carcinoma / keratoacanthoma', VASC:'Vascular lesions',
}
function ScoreRow({ item, rank }: { item: ClassificationResult['scores'][number]; rank: number }) {
  return <div className={`prediction-score-row${rank === 1 ? ' prediction-score-row--leading' : ''}`}>
    <span className="prediction-rank">{rank}</span>
    <div className="prediction-score-main"><div className="prediction-score-label"><span>{names[item.label] || item.label}</span><small>{item.label}</small></div>
      <progress value={item.score} max={1} aria-label={`${item.label} model score`} /></div>
    <strong>{(item.score*100).toFixed(1)}<span>%</span></strong>
  </div>
}
export function ClassificationSummary({ result }: { result: ClassificationResult }) {
  const sorted=[...result.scores].sort((a,b)=>b.score-a.score), first=sorted.slice(0,3), other=sorted.slice(3)
  const selected=result.scores.find(item=>item.label===result.leading_class)
  return <div className="classification-results">
    <div className="prediction-hero"><div><span className="prediction-overline">Selected model class</span><h3>{names[result.leading_class] || result.leading_class}</h3><span className="prediction-code">{result.leading_class}</span></div>
      <div className="prediction-primary-score"><span>Model score</span><strong>{selected ? (selected.score*100).toFixed(1) : '—'}<small>{selected ? '%' : ''}</small></strong></div></div>
    <div className="prediction-list-heading"><h4>Top {first.length} class scores</h4><span>Highest scores first</span></div>
    <div className="prediction-top-classes">{first.map((item,index)=><ScoreRow key={item.label} item={item} rank={index+1} />)}</div>
    {other.length>0 && <details className="prediction-other-classes"><summary><span className="prediction-expand-label">Show other {other.length} classes</span><span className="prediction-collapse-label">Hide other classes</span><ChevronDown size={17} /></summary><div>{other.map((item,index)=><ScoreRow key={item.label} item={item} rank={index+4} />)}</div></details>}
  </div>
}
